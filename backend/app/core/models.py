"""Domain models for the Atlas Fresh planning engine.

These are plain, framework-free dataclasses: no FastAPI, no Pydantic,
no I/O. They represent either validated source data (immutable input)
or calculated planning results (engine output). Nothing here imports
anything outside the Python standard library.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Segment(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# Quality rank: lower number = higher quality. Fixed by the business
# policy (A > B > C > D), never configurable.
SEGMENT_RANK: dict[Segment, int] = {
    Segment.A: 0,
    Segment.B: 1,
    Segment.C: 2,
    Segment.D: 3,
}
SEGMENT_ORDER: tuple[Segment, ...] = (Segment.A, Segment.B, Segment.C, Segment.D)


class AcceptanceMode(str, Enum):
    EXACT = "EXACT"
    MINIMUM = "MINIMUM"


class ClientStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNSERVED = "UNSERVED"


class ShortageReason(str, Enum):
    STATION_CAPACITY_REACHED = "STATION_CAPACITY_REACHED"
    INSUFFICIENT_COMPATIBLE_SEGMENT = "INSUFFICIENT_COMPATIBLE_SEGMENT"


# ----------------------------------------------------------------------
# Source / input data — validated upstream (Phase 4), immutable here.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Farm:
    farm_id: str
    name: str
    expected_capacity_t: float
    expected_mix: dict[Segment, float]  # fractions, validated to sum to 1.0
    actual: dict[Segment, int]  # tonnes, validated multiples of 5


@dataclass(frozen=True)
class Client:
    client_id: str
    name: str
    mode: AcceptanceMode
    requested_segment: Segment
    demand_t: int
    price_eur: int


@dataclass(frozen=True)
class Station:
    station_id: str
    capacity_t: int
    local_market_ratio: float
    reference_prices: dict[Segment, int]


# ----------------------------------------------------------------------
# Calculated / output data — produced only by the planning engine.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Allocation:
    farm_id: str
    segment: Segment
    client_id: str
    tonnes: int
    quality_upgrade: int
    unit_price_eur: int
    revenue_eur: int


@dataclass(frozen=True)
class ClientResult:
    client_id: str
    name: str
    mode: AcceptanceMode
    requested_segment: Segment
    price_eur: int
    demand_t: int
    allocated_t: int
    remaining_t: int
    status: ClientStatus
    reason: ShortageReason | None
    revenue_eur: int


@dataclass(frozen=True)
class FarmSegmentBalance:
    farm_id: str
    segment: Segment
    actual_t: int
    exported_t: int
    local_t: int
    expected_t: float
    variance_t: float


@dataclass(frozen=True)
class LocalResidualRow:
    farm_id: str
    segment: Segment
    tonnes_t: int
    reference_price_eur: int
    local_price_eur: float
    local_value_eur: float


@dataclass(frozen=True)
class SegmentVariance:
    segment: Segment
    expected_t: float
    actual_t: float
    variance_t: float


@dataclass(frozen=True)
class Kpis:
    expected_plan_t: float
    actual_received_t: float
    station_capacity_t: int
    actual_by_segment: dict[Segment, int]
    export_t: int
    export_rate: float | None  # None only if actual_received_t == 0
    local_volume_t: int
    export_revenue_eur: int
    local_value_eur: float
    total_value_eur: float
    at_risk_client_count: int

    @property
    def station_utilization(self) -> float | None:
        """exported / station capacity — the same formula approved in
        Phase 5 SS11, exposed as a derived property rather than a
        separately-computed field. Not stored; recomputed on access
        from already-computed values. None only if capacity is 0."""
        if self.station_capacity_t <= 0:
            return None
        return self.export_t / self.station_capacity_t


@dataclass(frozen=True)
class Narrative:
    overview: str
    local_residual: str


@dataclass(frozen=True)
class PlanResult:
    kpis: Kpis
    narrative: Narrative
    segment_variances: list[SegmentVariance]
    farm_segment_balances: list[FarmSegmentBalance]
    client_results: list[ClientResult]
    allocations: list[Allocation]
    local_residual: list[LocalResidualRow]