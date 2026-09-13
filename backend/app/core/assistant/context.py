"""Structured context builders for the AI assistant.

Pure functions: given an already-computed PlanResult, extract the
minimal slice of data needed to answer one of the three supported
questions. No calculation happens here beyond simple filtering/
sorting of fields the engine already computed. No FastAPI, no LLM
SDK, no I/O.
"""
from __future__ import annotations

from ..models import ClientStatus, PlanResult

SUPPORTED_QUESTIONS: tuple[str, ...] = ("at_risk_clients", "farm_gaps", "local_residual")

# Small, honest keyword router for free-text input. This is NOT an NLP
# classifier and must never be described as one — it is a minimal,
# transparent mapping from a handful of expected words to the three
# supported structured questions. Anything that doesn't match is
# correctly treated as unsupported rather than guessed at.
_FREE_TEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "at_risk_clients": ("risk", "client", "partial", "unserved"),
    "farm_gaps": ("farm", "segment", "gap", "variance", "production"),
    "local_residual": ("local", "residual", "unexported"),
}


def resolve_question_key(free_text: str) -> str | None:
    """Map free text to one of the supported question keys, or None if
    no supported question can be identified. Deliberately simple and
    literal — no fabricated understanding of anything else."""
    lowered = free_text.lower()
    for key, keywords in _FREE_TEXT_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return key
    return None


# ----------------------------------------------------------------------
# Loose relevance gate — for free text that does NOT match one of the
# three narrow buckets above, but is still a genuine question about
# today's plan (different phrasing, different language, a question the
# fixed three don't anticipate). This is intentionally broader than
# _FREE_TEXT_KEYWORDS: its only job is to filter out the CLEARLY
# unrelated ("book a truck", "what's the weather") before we spend an
# LLM call on it — it is not trying to classify the question, just to
# decide whether it plausibly belongs to this domain at all.
# ----------------------------------------------------------------------

_DOMAIN_VOCABULARY: tuple[str, ...] = (
    "farm", "client", "segment", "export", "local", "station", "capacity",
    "price", "tonne", "ton", "demand", "plan", "allocation", "allocate",
    "revenue", "risk", "gap", "residual", "variance", "supply", "quality",
)
# Deliberately excludes bare single-letter segment names ("a","b","c","d")
# — they collide with common English words ("a", "I") and produced false
# positives (e.g. "book A delivery truck" matching on "a"). "segment" on
# its own is enough of a signal without the letters.


def is_plausibly_relevant(free_text: str) -> bool:
    """True if the free text contains at least one word from today's
    domain vocabulary. Not a classifier, not NLP — a cheap filter that
    exists purely to avoid spending an LLM call on obviously unrelated
    questions. A real LLM call is still expected to refuse politely if
    this gate lets through something it genuinely can't answer."""
    words = set(free_text.lower().replace("?", " ").replace(",", " ").split())
    return any(word in words for word in _DOMAIN_VOCABULARY)


def build_full_context(plan: PlanResult) -> dict:
    """Serialize the ENTIRE PlanResult into a plain dict. Used only for
    a real LLM provider answering a free-text question that didn't
    match one of the three narrow buckets. Still pure, still no
    FastAPI/Pydantic — just a manual, explicit dataclass-to-dict walk
    so every field that leaves this module is visible in one place.

    This is intentionally larger than build_context()'s per-question
    slices; the documented "send the minimum necessary context"
    principle is honored by the relevance gate deciding WHETHER to
    call the LLM at all, not by further trimming what it sees once
    that decision is made — the whole plan is small (a few dozen rows
    total), so there is nothing meaningful left to trim."""
    k = plan.kpis
    return {
        "kpis": {
            "expected_plan_t": k.expected_plan_t,
            "actual_received_t": k.actual_received_t,
            "station_capacity_t": k.station_capacity_t,
            "actual_by_segment": {seg.value: t for seg, t in k.actual_by_segment.items()},
            "export_t": k.export_t,
            "export_rate": k.export_rate,
            "local_volume_t": k.local_volume_t,
            "export_revenue_eur": k.export_revenue_eur,
            "local_value_eur": k.local_value_eur,
            "total_value_eur": k.total_value_eur,
            "at_risk_client_count": k.at_risk_client_count,
        },
        "segment_variances": [
            {"segment": v.segment.value, "expected_t": v.expected_t, "actual_t": v.actual_t, "variance_t": v.variance_t}
            for v in plan.segment_variances
        ],
        "farm_segment_balances": [
            {"farm_id": b.farm_id, "segment": b.segment.value, "actual_t": b.actual_t, "exported_t": b.exported_t, "local_t": b.local_t}
            for b in plan.farm_segment_balances
        ],
        "client_results": [
            {
                "client_id": c.client_id,
                "name": c.name,
                "mode": c.mode.value,
                "requested_segment": c.requested_segment.value,
                "price_eur": c.price_eur,
                "demand_t": c.demand_t,
                "allocated_t": c.allocated_t,
                "remaining_t": c.remaining_t,
                "status": c.status.value,
                "reason": c.reason.value if c.reason else None,
            }
            for c in plan.client_results
        ],
        "allocations": [
            {
                "farm_id": a.farm_id,
                "segment": a.segment.value,
                "client_id": a.client_id,
                "tonnes": a.tonnes,
                "quality_upgrade": a.quality_upgrade,
                "revenue_eur": a.revenue_eur,
            }
            for a in plan.allocations
        ],
        "local_residual": [
            {"farm_id": r.farm_id, "segment": r.segment.value, "tonnes_t": r.tonnes_t, "local_value_eur": r.local_value_eur}
            for r in plan.local_residual
        ],
    }


def build_context(plan: PlanResult, question_key: str) -> dict:
    if question_key == "at_risk_clients":
        return _at_risk_clients_context(plan)
    if question_key == "farm_gaps":
        return _farm_gaps_context(plan)
    if question_key == "local_residual":
        return _local_residual_context(plan)
    raise ValueError(f"Unsupported question key: {question_key!r}")


def _at_risk_clients_context(plan: PlanResult) -> dict:
    at_risk = [c for c in plan.client_results if c.status != ClientStatus.COMPLETE]
    return {
        "question": "at_risk_clients",
        "clients": [
            {
                "client_id": c.client_id,
                "name": c.name,
                "status": c.status.value,
                "reason": c.reason.value if c.reason else None,
                "demand_t": c.demand_t,
                "allocated_t": c.allocated_t,
                "remaining_t": c.remaining_t,
            }
            for c in at_risk
        ],
        "at_risk_count": plan.kpis.at_risk_client_count,
    }


def _farm_gaps_context(plan: PlanResult) -> dict:
    # Most-negative variance first — the segment furthest below plan.
    variances = sorted(plan.segment_variances, key=lambda v: v.variance_t)
    return {
        "question": "farm_gaps",
        "segment_variances": [
            {
                "segment": v.segment.value,
                "expected_t": v.expected_t,
                "actual_t": v.actual_t,
                "variance_t": v.variance_t,
            }
            for v in variances
        ],
        # Local-residual farms are legitimate structured evidence of
        # "which farms' supply didn't find a client" — drawn straight
        # from PlanResult.local_residual, not recomputed.
        "local_residual_farms": [
            {"farm_id": r.farm_id, "segment": r.segment.value, "tonnes_t": r.tonnes_t}
            for r in plan.local_residual
        ],
    }


def _local_residual_context(plan: PlanResult) -> dict:
    return {
        "question": "local_residual",
        "local_volume_t": plan.kpis.local_volume_t,
        "local_value_eur": plan.kpis.local_value_eur,
        "rows": [
            {
                "farm_id": r.farm_id,
                "segment": r.segment.value,
                "tonnes_t": r.tonnes_t,
                "reference_price_eur": r.reference_price_eur,
                "local_price_eur": r.local_price_eur,
                "local_value_eur": r.local_value_eur,
            }
            for r in plan.local_residual
        ],
    }