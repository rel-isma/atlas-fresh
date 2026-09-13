"""Deterministic planning engine.

Implements the Atlas Fresh reference allocation policy exactly as
documented in the assessment brief. This module is pure: no FastAPI,
no HTTP, no database, no Excel loading, no UI, no AI/LLM calls. It
operates only on already-validated domain data (models.Farm,
models.Client, models.Station) and returns a models.PlanResult.

`allocate()` is the single public entry point. Everything else is a
private helper.
"""
from __future__ import annotations

from .models import (
    SEGMENT_ORDER,
    SEGMENT_RANK,
    AcceptanceMode,
    Allocation,
    Client,
    ClientResult,
    ClientStatus,
    Farm,
    FarmSegmentBalance,
    Kpis,
    LocalResidualRow,
    Narrative,
    PlanResult,
    Segment,
    ShortageReason,
    Station,
)
from .narrative import build_local_residual_narrative, build_overview_narrative


def allocate(farms: list[Farm], clients: list[Client], station: Station) -> PlanResult:
    """Run the deterministic reference policy and return the complete
    PlanResult. Pure function: same input always produces the same
    output."""

    supply = _build_supply(farms)
    ordered_clients = _order_clients(clients)

    allocations: list[Allocation] = []
    client_results: list[ClientResult] = []
    capacity_remaining = station.capacity_t

    for client in ordered_clients:
        client_allocations, allocated_t, capacity_remaining = _allocate_one_client(
            client, supply, capacity_remaining
        )
        allocations.extend(client_allocations)

        remaining_t = client.demand_t - allocated_t
        status = _derive_status(client.demand_t, allocated_t)
        reason = _derive_reason(status, capacity_remaining)
        revenue_eur = sum(a.revenue_eur for a in client_allocations)

        client_results.append(
            ClientResult(
                client_id=client.client_id,
                name=client.name,
                mode=client.mode,
                requested_segment=client.requested_segment,
                price_eur=client.price_eur,
                demand_t=client.demand_t,
                allocated_t=allocated_t,
                remaining_t=remaining_t,
                status=status,
                reason=reason,
                revenue_eur=revenue_eur,
            )
        )

    farm_segment_balances = _build_farm_segment_balances(farms, supply)
    local_residual = _build_local_residual(supply, station)
    segment_variances = _build_segment_variances(farms)
    kpis = _build_kpis(farms, client_results, allocations, local_residual, station)

    narrative = Narrative(
        overview=build_overview_narrative(kpis, segment_variances),
        local_residual=build_local_residual_narrative(local_residual, kpis),
    )

    return PlanResult(
        kpis=kpis,
        narrative=narrative,
        segment_variances=segment_variances,
        farm_segment_balances=farm_segment_balances,
        client_results=client_results,
        allocations=allocations,
        local_residual=local_residual,
    )


# ----------------------------------------------------------------------
# Client ordering (policy step 4): price DESC, client_id ASC tie-break.
# No other key is ever used.
# ----------------------------------------------------------------------


def _order_clients(clients: list[Client]) -> list[Client]:
    return sorted(clients, key=lambda c: (-c.price_eur, c.client_id))


# ----------------------------------------------------------------------
# Supply ledger: (farm_id, segment) -> tonnes remaining. Built once from
# actual A/B/C/D tonnes. Planned/expected values never enter this ledger
# — they are comparison-only (policy step 3).
# ----------------------------------------------------------------------


def _build_supply(farms: list[Farm]) -> dict[tuple[str, Segment], int]:
    supply: dict[tuple[str, Segment], int] = {}
    for farm in farms:
        for segment in SEGMENT_ORDER:
            supply[(farm.farm_id, segment)] = farm.actual[segment]
    return supply


# ----------------------------------------------------------------------
# Compatibility + candidate ordering (policy steps 5-6).
# ----------------------------------------------------------------------


def _compatible_segments(mode: AcceptanceMode, requested: Segment) -> list[Segment]:
    if mode is AcceptanceMode.EXACT:
        return [requested]
    # MINIMUM: requested segment or anything better (lower rank).
    requested_rank = SEGMENT_RANK[requested]
    return [s for s in SEGMENT_ORDER if SEGMENT_RANK[s] <= requested_rank]


def _quality_upgrade(requested: Segment, candidate: Segment) -> int:
    return SEGMENT_RANK[requested] - SEGMENT_RANK[candidate]


def _ranked_candidates(
    supply: dict[tuple[str, Segment], int],
    farms_in_order: list[str],
    compatible_segments: list[Segment],
    requested: Segment,
) -> list[tuple[int, str, Segment]]:
    """Positive-balance (upgrade, farm_id, segment) candidates, sorted by
    upgrade ASC then farm_id ASC."""
    candidates = [
        (_quality_upgrade(requested, segment), farm_id, segment)
        for farm_id in farms_in_order
        for segment in compatible_segments
        if supply.get((farm_id, segment), 0) > 0
    ]
    candidates.sort(key=lambda c: (c[0], c[1]))
    return candidates


# ----------------------------------------------------------------------
# Allocation for a single client, in strict candidate order, consuming
# both the client's remaining demand and the shared station capacity.
# One pass — no second stage, no redistribution.
# ----------------------------------------------------------------------


def _allocate_one_client(
    client: Client,
    supply: dict[tuple[str, Segment], int],
    capacity_remaining: int,
) -> tuple[list[Allocation], int, int]:
    compatible = _compatible_segments(client.mode, client.requested_segment)
    farm_ids_sorted = sorted({fid for (fid, _seg) in supply.keys()})
    candidates = _ranked_candidates(supply, farm_ids_sorted, compatible, client.requested_segment)

    allocations: list[Allocation] = []
    remaining_demand = client.demand_t

    for upgrade, farm_id, segment in candidates:
        if remaining_demand <= 0 or capacity_remaining <= 0:
            break
        available = supply[(farm_id, segment)]
        take = min(remaining_demand, available, capacity_remaining)
        if take <= 0:
            continue
        assert take % 5 == 0, "allocation step produced a non-5t quantity"

        supply[(farm_id, segment)] -= take
        remaining_demand -= take
        capacity_remaining -= take

        allocations.append(
            Allocation(
                farm_id=farm_id,
                segment=segment,
                client_id=client.client_id,
                tonnes=take,
                quality_upgrade=upgrade,
                unit_price_eur=client.price_eur,
                revenue_eur=take * client.price_eur,
            )
        )

    allocated_t = client.demand_t - remaining_demand
    return allocations, allocated_t, capacity_remaining


# ----------------------------------------------------------------------
# Status + shortage reason (policy: COMPLETE/PARTIAL/UNSERVED + the two
# named reasons).
# ----------------------------------------------------------------------


def _derive_status(demand_t: int, allocated_t: int) -> ClientStatus:
    if allocated_t == demand_t:
        return ClientStatus.COMPLETE
    if allocated_t == 0:
        return ClientStatus.UNSERVED
    return ClientStatus.PARTIAL


def _derive_reason(status: ClientStatus, capacity_remaining: int) -> ShortageReason | None:
    if status is ClientStatus.COMPLETE:
        return None

    # RECOMMENDED IMPLEMENTATION (not stated verbatim by the brief):
    # check capacity first, mirroring the brief's own sentence structure
    # ("if capacity is exhausted, use X; otherwise, use Y"). This is the
    # documented, labeled resolution for the case where both conditions
    # could coincide — see Phase 5 ambiguity note. It has zero effect on
    # the supplied baseline, where no client triggers both simultaneously.
    if capacity_remaining <= 0:
        return ShortageReason.STATION_CAPACITY_REACHED

    return ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT


# ----------------------------------------------------------------------
# Farm/segment balances (actual = exported + local, by construction).
# ----------------------------------------------------------------------


def _build_farm_segment_balances(
    farms: list[Farm], supply_after: dict[tuple[str, Segment], int]
) -> list[FarmSegmentBalance]:
    balances: list[FarmSegmentBalance] = []
    for farm in farms:
        for segment in SEGMENT_ORDER:
            actual_t = farm.actual[segment]
            if actual_t <= 0:
                continue
            local_t = supply_after[(farm.farm_id, segment)]
            exported_t = actual_t - local_t
            balances.append(
                FarmSegmentBalance(
                    farm_id=farm.farm_id,
                    segment=segment,
                    actual_t=actual_t,
                    exported_t=exported_t,
                    local_t=local_t,
                )
            )
    return balances


# ----------------------------------------------------------------------
# Local residual (policy step 8): everything left in the supply ledger
# after all clients are processed. Computed from the SAME ledger the
# client loop consumed from — not a separate subtraction — so it cannot
# drift from "actual - exported" by construction.
# ----------------------------------------------------------------------


def _build_local_residual(
    supply_after: dict[tuple[str, Segment], int], station: Station
) -> list[LocalResidualRow]:
    rows: list[LocalResidualRow] = []
    for (farm_id, segment), tonnes in sorted(supply_after.items()):
        if tonnes <= 0:
            continue
        reference_price = station.reference_prices[segment]
        local_price = station.local_market_ratio * reference_price
        local_value = tonnes * local_price
        rows.append(
            LocalResidualRow(
                farm_id=farm_id,
                segment=segment,
                tonnes_t=tonnes,
                reference_price_eur=reference_price,
                local_price_eur=local_price,
                local_value_eur=local_value,
            )
        )
    return rows


# ----------------------------------------------------------------------
# Segment variance (comparison-only, never feeds allocation).
# ----------------------------------------------------------------------


def _build_segment_variances(farms: list[Farm]):
    from .models import SegmentVariance

    variances = []
    for segment in SEGMENT_ORDER:
        expected_t = sum(f.expected_capacity_t * f.expected_mix[segment] for f in farms)
        actual_t = sum(f.actual[segment] for f in farms)
        variances.append(
            SegmentVariance(segment=segment, expected_t=expected_t, actual_t=actual_t, variance_t=actual_t - expected_t)
        )
    return variances


# ----------------------------------------------------------------------
# KPIs.
# ----------------------------------------------------------------------


def _build_kpis(
    farms: list[Farm],
    client_results: list[ClientResult],
    allocations: list[Allocation],
    local_residual: list[LocalResidualRow],
    station: Station,
) -> Kpis:
    expected_plan_t = sum(f.expected_capacity_t for f in farms)
    actual_by_segment = {
        segment: sum(f.actual[segment] for f in farms) for segment in SEGMENT_ORDER
    }
    actual_received_t = sum(actual_by_segment.values())
    export_t = sum(a.tonnes for a in allocations)
    local_volume_t = sum(r.tonnes_t for r in local_residual)
    export_revenue_eur = sum(a.revenue_eur for a in allocations)
    local_value_eur = sum(r.local_value_eur for r in local_residual)
    at_risk_client_count = sum(1 for c in client_results if c.status != ClientStatus.COMPLETE)

    export_rate = (export_t / actual_received_t) if actual_received_t > 0 else None

    return Kpis(
        expected_plan_t=expected_plan_t,
        actual_received_t=actual_received_t,
        station_capacity_t=station.capacity_t,
        actual_by_segment=actual_by_segment,
        export_t=export_t,
        export_rate=export_rate,
        local_volume_t=local_volume_t,
        export_revenue_eur=export_revenue_eur,
        local_value_eur=local_value_eur,
        total_value_eur=export_revenue_eur + local_value_eur,
        at_risk_client_count=at_risk_client_count,
    )
