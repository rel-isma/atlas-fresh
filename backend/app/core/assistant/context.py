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
