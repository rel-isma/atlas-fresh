"""Guards the boundary between whatever produced an answer (fallback or
a future real provider) and what the user sees.

Pure functions, no I/O. This is what makes "reject unknown IDs" and
"never fabricate a citation" real mechanisms rather than policy
statements — every ID a provider claims to cite is checked against the
actual PlanResult before it is trusted.
"""
from __future__ import annotations

import re

from ..models import PlanResult

_PLAN_ID_PATTERN = re.compile(r"\b[CF]\d+\b")


def known_ids(plan: PlanResult) -> set[str]:
    """Every farm_id and client_id that genuinely exists in this
    PlanResult — the only IDs an answer is ever allowed to cite."""
    farm_ids = {b.farm_id for b in plan.farm_segment_balances}
    client_ids = {c.client_id for c in plan.client_results}
    return farm_ids | client_ids


def validate_cited_ids(cited_ids: list[str], plan: PlanResult) -> list[str]:
    """Return only real cited IDs for callers that need a filtered view.

    API responses use ``ensure_grounded`` instead, which is intentionally
    strict and rejects the entire answer when any unknown ID is present.
    """
    valid = known_ids(plan)
    return [cid for cid in cited_ids if cid in valid]


def extract_referenced_ids(answer: str) -> list[str]:
    """Extract farm/client identifiers mentioned in answer text."""
    return list(dict.fromkeys(_PLAN_ID_PATTERN.findall(answer)))


class UngroundedAnswerError(Exception):
    """Raised when an answer references any unknown farm/client ID."""


def ensure_grounded(
    cited_ids: list[str],
    plan: PlanResult,
    *,
    answer: str = "",
) -> list[str]:
    """Reject an answer if any claimed or visible plan ID is unknown."""
    claimed_ids = list(dict.fromkeys(cited_ids + extract_referenced_ids(answer)))
    valid = known_ids(plan)
    unknown_ids = [cid for cid in claimed_ids if cid not in valid]
    if unknown_ids:
        raise UngroundedAnswerError(
            f"Answer referenced unknown IDs: {', '.join(unknown_ids)}"
        )
    return claimed_ids
