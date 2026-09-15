"""Narrative text generation.

Pure functions that turn already-computed KPIs / segment variances /
local residual rows into human-readable sentences. Nothing here is
hardcoded to today's snapshot: the "worst" segment, the local-residual
segment mix, and every number are derived dynamically from whatever
PlanResult the engine actually produced.
"""
from __future__ import annotations

from .models import Kpis, LocalResidualRow, SegmentVariance


def build_overview_narrative(kpis: Kpis, segment_variances: list[SegmentVariance]) -> str:
    worst = min(segment_variances, key=lambda v: v.variance_t)
    direction = "short of" if worst.variance_t < 0 else "above"

    export_rate_pct = f"{kpis.export_rate:.1%}" if kpis.export_rate is not None else "n/a"

    return (
        f"{kpis.actual_received_t:.0f}t actual vs {kpis.expected_plan_t:.0f}t planned "
        f"(Segment {worst.segment.value} {direction} plan by {abs(worst.variance_t):.1f}t). "
        f"{kpis.export_t:.0f}t exported at {export_rate_pct} of actual, "
        f"generating €{kpis.export_revenue_eur:,.0f}. "
        f"{kpis.local_volume_t:.0f}t (€{kpis.local_value_eur:,.0f}) went local. "
        f"{kpis.at_risk_client_count} client(s) are partial or unserved."
    )


def build_local_residual_narrative(
    local_residual: list[LocalResidualRow],
    kpis: Kpis,
) -> str:
    if not local_residual:
        return "All actual production was exported today — no local-market residual."

    segments_involved = sorted({row.segment.value for row in local_residual})
    farms_involved = sorted({row.farm_id for row in local_residual})

    if len(segments_involved) == 1:
        segment_phrase = f"Segment {segments_involved[0]}"
    else:
        segment_phrase = "Segments " + ", ".join(segments_involved)

    local_ratio_pct = f"{kpis.local_market_ratio * 100:.2f}".rstrip("0").rstrip(".")

    return (
        f"{kpis.local_volume_t:.0f}t (€{kpis.local_value_eur:,.0f}) had no remaining compatible "
        f"demand within station capacity and went to the local market at "
        f"{local_ratio_pct}% of reference price. "
        f"This residual is entirely {segment_phrase}, from {len(farms_involved)} farm(s): "
        f"{', '.join(farms_involved)}."
    )
