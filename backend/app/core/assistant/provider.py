"""Assistant provider abstraction.

A "provider" answers one of the three supported questions given an
already-built context dict. This module defines that abstraction and
FallbackProvider: a deterministic, dependency-free implementation that
is always available, built entirely from PlanResult data.

A real LLM-backed provider can be added later behind the same
AssistantProvider interface without touching context.py, guard.py, or
the API routes. Importing this module never requires an API key or
network access — there is no mandatory external dependency here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import PlanResult


@dataclass(frozen=True)
class ProviderResult:
    answer: str
    cited_ids: list[str]
    source: str  # "llm" | "fallback"


class AssistantProvider(Protocol):
    def answer(
        self,
        *,
        question_key: str | None,
        question_text: str | None,
        context: dict,
        plan: PlanResult,
    ) -> ProviderResult: ...


class FallbackProvider:
    """Always available. Builds a plain-language answer directly from
    the structured context passed in — no network call, no API key,
    no external dependency. This is what runs when no real provider is
    configured, or when a real provider fails or times out.

    FallbackProvider only understands the three narrow, pre-built
    contexts from context.build_context() — it has no way to reason
    over free text, so question_key must be one of the three supported
    keys. question_text is accepted (for interface compatibility with
    a real LLM provider) but ignored."""

    def answer(
        self,
        *,
        question_key: str | None,
        question_text: str | None = None,
        context: dict,
        plan: PlanResult,
    ) -> ProviderResult:
        if question_key == "at_risk_clients":
            return self._at_risk_clients(context)
        if question_key == "farm_gaps":
            return self._farm_gaps(context)
        if question_key == "local_residual":
            return self._local_residual(context)
        raise ValueError(f"Unsupported question key: {question_key!r}")

    # -- at_risk_clients --------------------------------------------

    def _at_risk_clients(self, context: dict) -> ProviderResult:
        clients = context["clients"]
        if not clients:
            return ProviderResult(
                answer="No clients are at risk today — every client's demand was fully allocated.",
                cited_ids=[],
                source="fallback",
            )

        reason_text = {
            "STATION_CAPACITY_REACHED": "station capacity was fully used before this order could be completed",
            "INSUFFICIENT_COMPATIBLE_SEGMENT": "no compatible supply remained after higher-priority orders were served",
        }

        parts: list[str] = []
        cited_ids: list[str] = []
        for c in clients:
            reason = reason_text.get(c["reason"], "the order could not be fully served")
            parts.append(
                f"{c['client_id']} ({c['name']}) is {c['status'].lower()} — "
                f"{c['allocated_t']:.0f}/{c['demand_t']:.0f}t allocated because {reason}."
            )
            cited_ids.append(c["client_id"])

        answer = f"{len(clients)} client(s) are at risk today. " + " ".join(parts)
        return ProviderResult(answer=answer, cited_ids=cited_ids, source="fallback")

    # -- farm_gaps ----------------------------------------------------

    def _farm_gaps(self, context: dict) -> ProviderResult:
        variances = context["segment_variances"]
        worst = variances[0]  # already sorted ascending: most negative first
        residual_farms = context["local_residual_farms"]
        cited_ids = sorted({r["farm_id"] for r in residual_farms})

        direction = "short of" if worst["variance_t"] < 0 else "above"
        answer = (
            f"Segment {worst['segment']} is the largest gap today: "
            f"{worst['actual_t']:.1f}t actual vs {worst['expected_t']:.1f}t expected "
            f"({direction} plan by {abs(worst['variance_t']):.1f}t)."
        )
        if residual_farms:
            residual_segment = residual_farms[0]["segment"]
            answer += (
                f" Separately, {len(cited_ids)} farm(s) ({', '.join(cited_ids)}) had Segment "
                f"{residual_segment} supply that went to the local market rather than export."
            )
        return ProviderResult(answer=answer, cited_ids=cited_ids, source="fallback")

    # -- local_residual -------------------------------------------------

    def _local_residual(self, context: dict) -> ProviderResult:
        volume = context["local_volume_t"]
        value = context["local_value_eur"]
        rows = context["rows"]

        if volume <= 0:
            return ProviderResult(
                answer="No tonnes went to the local market today — all actual production was exported.",
                cited_ids=[],
                source="fallback",
            )

        segments = sorted({r["segment"] for r in rows})
        farm_ids = sorted({r["farm_id"] for r in rows})
        segment_phrase = f"Segment {segments[0]}" if len(segments) == 1 else "Segments " + ", ".join(segments)

        answer = (
            f"{volume:.0f}t (€{value:,.0f}) went to the local market today. This is what remained "
            f"after export allocation was complete — it was not individually rejected tonne by "
            f"tonne, it is simply the actual production that had no remaining compatible demand "
            f"within station capacity. The residual is entirely {segment_phrase}, from farms: "
            f"{', '.join(farm_ids)}."
        )
        return ProviderResult(answer=answer, cited_ids=farm_ids, source="fallback")


def get_default_provider() -> "AssistantProvider":
    """Factory for the assistant provider. Reads ANTHROPIC_API_KEY from
    the environment: if it's set and the `anthropic` package is
    installed, returns a real LLMProvider; otherwise (no key, package
    missing, or construction fails for any reason) falls back to the
    always-available FallbackProvider. Callers never construct a
    specific provider class directly — this is the only place that
    decision is made."""
    import os

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return LLMProvider()
        except Exception:
            # No installed SDK, bad key format, etc. — fail open to
            # the deterministic fallback rather than breaking the
            # assistant endpoint entirely.
            return FallbackProvider()
    return FallbackProvider()


class LLMProvider:
    """Real LLM-backed provider. Only constructed when ANTHROPIC_API_KEY
    is set (see get_default_provider). Imports the `anthropic` package
    lazily, inside __init__ — so importing this module, and every
    other provider/context/guard module, never requires that package
    to be installed. If it isn't installed, __init__ raises and the
    factory falls back to FallbackProvider.

    Grounding is enforced in two layers:
      1. The system prompt instructs the model to answer ONLY from the
         provided context, to cite real IDs exactly as given, and to
         say the question is unanswerable if the context doesn't cover
         it.
      2. Regardless of what the model claims, guard.py independently
         re-checks every cited ID against the real PlanResult after
         this provider returns — this class is trusted for wording,
         never trusted for correctness of citations.
    """

    def __init__(self) -> None:
        import os

        import anthropic  # raises ImportError here if not installed

        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def answer(
        self,
        *,
        question_key: str | None,
        question_text: str | None,
        context: dict,
        plan: PlanResult,
    ) -> ProviderResult:
        import json

        question = question_text or (question_key or "").replace("_", " ")
        system_prompt = (
            "You are explaining a computed apple-export plan to a Production/Commercial "
            "manager. You do NOT calculate anything — a deterministic engine already did. "
            "Answer ONLY using the JSON context provided below; never invent a number, "
            "farm ID, or client ID that is not present in it. When you refer to a farm or "
            "client, use its exact ID as written in the context (e.g. 'C02', 'F15'). "
            "If the context does not contain enough information to answer, say so plainly "
            "instead of guessing. Keep the answer to a few sentences."
        )
        user_message = f"Context (JSON):\n{json.dumps(context)}\n\nQuestion: {question}"

        response = self._client.messages.create(
            model=self._model,
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        answer_text = "".join(block.text for block in response.content if block.type == "text")

        # Extract cited IDs by simple pattern match (C## / F##) rather
        # than trusting the model to also return a structured list —
        # guard.py will independently validate every ID found this way
        # against the real PlanResult before anything is shown.
        cited_ids = self._extract_ids(answer_text)

        return ProviderResult(answer=answer_text, cited_ids=cited_ids, source="llm")

    @staticmethod
    def _extract_ids(text: str) -> list[str]:
        import re

        found = re.findall(r"\b[CF]\d{2}\b", text)
        # De-duplicate while preserving first-seen order.
        seen: list[str] = []
        for fid in found:
            if fid not in seen:
                seen.append(fid)
        return seen