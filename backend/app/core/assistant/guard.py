"""Guards the boundary between whatever produced an answer (fallback or
a future real provider) and what the user sees.

Pure functions, no I/O. This is what makes "reject unknown IDs" and
"never fabricate a citation" real mechanisms rather than policy
statements — every ID a provider claims to cite is checked against the
actual PlanResult before it is trusted.
"""
from __future__ import annotations

from ..models import PlanResult


def known_ids(plan: PlanResult) -> set[str]:
    """Every farm_id and client_id that genuinely exists in this
    PlanResult — the only IDs an answer is ever allowed to cite."""
    farm_ids = {b.farm_id for b in plan.farm_segment_balances}
    client_ids = {c.client_id for c in plan.client_results}
    return farm_ids | client_ids


def validate_cited_ids(cited_ids: list[str], plan: PlanResult) -> list[str]:
    """Return only the cited IDs that are real. Unknown IDs are
    dropped silently rather than raising, so a mostly-good answer with
    one bad reference stays usable — but nothing fabricated is ever
    shown."""
    valid = known_ids(plan)
    return [cid for cid in cited_ids if cid in valid]


class UngroundedAnswerError(Exception):
    """Raised when an answer cannot be trusted as grounded — e.g. it
    claimed citations but every single one turned out to be unknown."""


def ensure_grounded(cited_ids: list[str], plan: PlanResult) -> list[str]:
    """Validate cited IDs; raise if the answer claimed citations but
    none of them are real (a strong signal something is fabricated,
    not just imprecise)."""
    valid_cited = validate_cited_ids(cited_ids, plan)
    if cited_ids and not valid_cited:
        raise UngroundedAnswerError(
            "Answer cited only unknown IDs — rejecting rather than showing a fabricated reference."
        )
    return valid_cited
