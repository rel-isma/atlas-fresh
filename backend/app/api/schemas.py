"""Pydantic schemas for the HTTP API boundary.

These are the ONLY place Pydantic is used in the backend. The domain
models (app/core/models.py) remain plain dataclasses and never import
Pydantic or FastAPI — this module is the translation layer between
them and JSON.

Every schema exposes camelCase field names in JSON while staying
snake_case internally, via a shared alias generator. Each schema has a
`from_domain(...)` classmethod that does the field-by-field mapping
explicitly — no implicit/automatic dataclass-to-Pydantic conversion —
so every mapping is visible and reviewable in one place.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from ..core.loader import LoaderIssue
from ..core.models import (
    Allocation,
    ClientResult,
    ClientStatusSummary,
    FarmSegmentBalance,
    FarmSummary,
    Kpis,
    LocalResidualRow,
    Narrative,
    PlanResult,
    SegmentVariance,
)
from ..core.validation import ValidationIssue


def _to_camel(snake: str) -> str:
    first, *rest = snake.split("_")
    return first + "".join(word.capitalize() for word in rest)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        extra="forbid",
    )


SegmentValue = Literal["A", "B", "C", "D"]
ClientModeValue = Literal["EXACT", "MINIMUM"]
ClientStatusValue = Literal["COMPLETE", "PARTIAL", "UNSERVED"]
ShortageReasonValue = Literal[
    "STATION_CAPACITY_REACHED", "INSUFFICIENT_COMPATIBLE_SEGMENT"
]
VarianceDirectionValue = Literal["BELOW", "ON_PLAN", "ABOVE"]


# ----------------------------------------------------------------------
# Validation / data-health schemas
# ----------------------------------------------------------------------


class ValidationIssueSchema(CamelModel):
    sheet: str
    id: str | None
    field: str | None
    message: str

    @classmethod
    def from_domain(cls, issue: ValidationIssue | LoaderIssue) -> "ValidationIssueSchema":
        # LoaderIssue (structural problems) has no id/field — normalize
        # both shapes into the same schema so the API always returns
        # one consistent validationErrors shape.
        if isinstance(issue, ValidationIssue):
            return cls(sheet=issue.sheet, id=issue.id, field=issue.field, message=issue.message)
        return cls(sheet=issue.sheet, id=None, field=None, message=issue.message)


class InvalidPlanResponse(CamelModel):
    data_health: Literal["invalid"] = "invalid"
    validation_errors: list[ValidationIssueSchema]


# ----------------------------------------------------------------------
# PlanResult schemas
# ----------------------------------------------------------------------


class KpisSchema(CamelModel):
    expected_plan_t: float
    actual_received_t: float
    station_capacity_t: int
    local_market_ratio: float
    actual_by_segment: dict[SegmentValue, int]
    export_t: int
    export_rate: float | None
    station_utilization: float | None
    local_volume_t: int
    export_revenue_eur: int
    local_value_eur: float
    total_value_eur: float
    at_risk_count: int

    @classmethod
    def from_domain(cls, k: Kpis) -> "KpisSchema":
        return cls(
            expected_plan_t=k.expected_plan_t,
            actual_received_t=k.actual_received_t,
            station_capacity_t=k.station_capacity_t,
            local_market_ratio=k.local_market_ratio,
            actual_by_segment={seg.value: t for seg, t in k.actual_by_segment.items()},
            export_t=k.export_t,
            export_rate=k.export_rate,
            station_utilization=k.station_utilization,
            local_volume_t=k.local_volume_t,
            export_revenue_eur=k.export_revenue_eur,
            local_value_eur=k.local_value_eur,
            total_value_eur=k.total_value_eur,
            at_risk_count=k.at_risk_client_count,
        )


class ClientStatusSummarySchema(CamelModel):
    client_count: int
    complete_count: int
    partial_count: int
    unserved_count: int
    complete_pct: float
    partial_pct: float
    unserved_pct: float
    partial_end_pct: float

    @classmethod
    def from_domain(
        cls, summary: ClientStatusSummary
    ) -> "ClientStatusSummarySchema":
        return cls(
            client_count=summary.client_count,
            complete_count=summary.complete_count,
            partial_count=summary.partial_count,
            unserved_count=summary.unserved_count,
            complete_pct=summary.complete_pct,
            partial_pct=summary.partial_pct,
            unserved_pct=summary.unserved_pct,
            partial_end_pct=summary.partial_end_pct,
        )


class NarrativeSchema(CamelModel):
    overview: str
    local_residual: str

    @classmethod
    def from_domain(cls, n: Narrative) -> "NarrativeSchema":
        return cls(overview=n.overview, local_residual=n.local_residual)


class SegmentVarianceSchema(CamelModel):
    segment: SegmentValue
    expected_t: float
    actual_t: float
    variance_t: float

    @classmethod
    def from_domain(cls, v: SegmentVariance) -> "SegmentVarianceSchema":
        return cls(segment=v.segment.value, expected_t=v.expected_t, actual_t=v.actual_t, variance_t=v.variance_t)


class FarmSegmentBalanceSchema(CamelModel):
    farm_id: str
    segment: SegmentValue
    actual_t: int
    exported_t: int
    local_t: int
    expected_t: float
    variance_t: float
    variance_direction: VarianceDirectionValue

    @classmethod
    def from_domain(cls, b: FarmSegmentBalance) -> "FarmSegmentBalanceSchema":
        return cls(
            farm_id=b.farm_id,
            segment=b.segment.value,
            actual_t=b.actual_t,
            exported_t=b.exported_t,
            local_t=b.local_t,
            expected_t=b.expected_t,
            variance_t=b.variance_t,
            variance_direction=b.variance_direction.value,
        )


class FarmSummarySchema(CamelModel):
    farm_id: str
    expected_t: float
    actual_t: int
    local_t: int
    variance_t: float
    below_plan: bool

    @classmethod
    def from_domain(cls, farm: FarmSummary) -> "FarmSummarySchema":
        return cls(
            farm_id=farm.farm_id,
            expected_t=farm.expected_t,
            actual_t=farm.actual_t,
            local_t=farm.local_t,
            variance_t=farm.variance_t,
            below_plan=farm.below_plan,
        )


class ClientResultSchema(CamelModel):
    client_id: str
    name: str
    mode: ClientModeValue
    requested_segment: SegmentValue
    price_eur: int
    demand_t: int
    allocated_t: int
    remaining_t: int
    status: ClientStatusValue
    reason: ShortageReasonValue | None
    revenue_eur: int

    @classmethod
    def from_domain(cls, c: ClientResult) -> "ClientResultSchema":
        return cls(
            client_id=c.client_id,
            name=c.name,
            mode=c.mode.value,
            requested_segment=c.requested_segment.value,
            price_eur=c.price_eur,
            demand_t=c.demand_t,
            allocated_t=c.allocated_t,
            remaining_t=c.remaining_t,
            status=c.status.value,
            reason=c.reason.value if c.reason else None,
            revenue_eur=c.revenue_eur,
        )


class AllocationSchema(CamelModel):
    farm_id: str
    segment: SegmentValue
    client_id: str
    tonnes: int
    quality_upgrade: int
    unit_price_eur: int
    revenue_eur: int

    @classmethod
    def from_domain(cls, a: Allocation) -> "AllocationSchema":
        return cls(
            farm_id=a.farm_id,
            segment=a.segment.value,
            client_id=a.client_id,
            tonnes=a.tonnes,
            quality_upgrade=a.quality_upgrade,
            unit_price_eur=a.unit_price_eur,
            revenue_eur=a.revenue_eur,
        )


class LocalResidualRowSchema(CamelModel):
    farm_id: str
    segment: SegmentValue
    tonnes_t: int
    reference_price_eur: int
    local_price_eur: float
    local_value_eur: float

    @classmethod
    def from_domain(cls, r: LocalResidualRow) -> "LocalResidualRowSchema":
        return cls(
            farm_id=r.farm_id,
            segment=r.segment.value,
            tonnes_t=r.tonnes_t,
            reference_price_eur=r.reference_price_eur,
            local_price_eur=r.local_price_eur,
            local_value_eur=r.local_value_eur,
        )


class PlanResultSchema(CamelModel):
    data_health: Literal["healthy"] = "healthy"
    kpis: KpisSchema
    client_status_summary: ClientStatusSummarySchema
    narrative: NarrativeSchema
    segment_variances: list[SegmentVarianceSchema]
    farm_summaries: list[FarmSummarySchema]
    farm_segment_balances: list[FarmSegmentBalanceSchema]
    client_results: list[ClientResultSchema]
    allocations: list[AllocationSchema]
    local_residual: list[LocalResidualRowSchema]

    @classmethod
    def from_domain(cls, plan: PlanResult) -> "PlanResultSchema":
        return cls(
            kpis=KpisSchema.from_domain(plan.kpis),
            client_status_summary=ClientStatusSummarySchema.from_domain(
                plan.client_status_summary
            ),
            narrative=NarrativeSchema.from_domain(plan.narrative),
            segment_variances=[SegmentVarianceSchema.from_domain(v) for v in plan.segment_variances],
            farm_summaries=[FarmSummarySchema.from_domain(f) for f in plan.farm_summaries],
            farm_segment_balances=[FarmSegmentBalanceSchema.from_domain(b) for b in plan.farm_segment_balances],
            client_results=[ClientResultSchema.from_domain(c) for c in plan.client_results],
            allocations=[AllocationSchema.from_domain(a) for a in plan.allocations],
            local_residual=[LocalResidualRowSchema.from_domain(r) for r in plan.local_residual],
        )


# ----------------------------------------------------------------------
# Assistant schemas
# ----------------------------------------------------------------------


FreeText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class AssistantRequest(CamelModel):
    """Exactly one of `question` / `freeText` must be provided.

    `question` is restricted to the 3 known chip values — this is a
    programmatic selector the UI sends when the user taps a suggested
    question, never something a person types. Anything else in this
    field is rejected by Pydantic itself (422) before the route even
    runs, rather than silently falling through to "unsupported".

    `freeText` is the only field a human-typed question belongs in.
    """

    question: Literal["at_risk_clients", "farm_gaps", "local_residual"] | None = None
    free_text: FreeText | None = None

    @model_validator(mode="after")
    def _exactly_one_field(self) -> "AssistantRequest":
        if bool(self.question) == bool(self.free_text):
            raise ValueError(
                "Provide exactly one of 'question' (a fixed chip value) or 'freeText' (a typed question) — not both, not neither."
            )
        return self


class AssistantAvailableResponse(CamelModel):
    available: Literal[True] = True
    answer: str
    cited_ids: list[str]
    source: Literal["llm", "fallback"]


class AssistantUnavailableResponse(CamelModel):
    available: Literal[False] = False
    reason: str
    source: Literal["fallback"] = "fallback"
    fallback_answer: str | None = None
