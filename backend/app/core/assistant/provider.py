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
    def answer(self, question_key: str, context: dict, plan: PlanResult) -> ProviderResult: ...


class FallbackProvider:
    """Always available. Builds a plain-language answer directly from
    the structured context passed in — no network call, no API key,
    no external dependency. This is what runs when no real provider is
    configured, or when a real provider fails or times out."""

    def answer(self, question_key: str, context: dict, plan: PlanResult) -> ProviderResult:
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


def get_default_provider() -> FallbackProvider:
    """Factory for the always-available fallback provider. A real
    provider (reading configuration such as an API key from the
    environment) can be wired in here later without changing any
    caller — routes call this factory, never construct a specific
    provider class directly. No such provider is configured in this
    phase; only the fallback exists."""
    return FallbackProvider()
