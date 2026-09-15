"""Business validation for the Atlas Fresh workbook.

Pure functions only: no I/O, no openpyxl, no FastAPI. Consumes the raw
dicts produced by loader.py and either:
  - returns a list of ValidationIssue (input is not well-formed), or
  - builds typed domain objects (models.Farm/Client/Station) that the
    planning engine can safely assume are valid.

Validation answers "is the input well-formed?". It never answers "what
does the input imply?" — that is the engine's job (engine.py).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TypeGuard

from .loader import RawWorkbook
from .models import AcceptanceMode, Client, Farm, Segment, Station

TOLERANCE = 1e-6
VALID_SEGMENTS = {"A", "B", "C", "D"}
VALID_MODES = {"EXACT", "MINIMUM"}
FARM_ID_PATTERN = re.compile(r"F\d+")
CLIENT_ID_PATTERN = re.compile(r"C\d+")


@dataclass(frozen=True)
class ValidationIssue:
    sheet: str
    id: str | None
    field: str | None
    message: str


def _is_number(value: object) -> TypeGuard[int | float]:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _is_integer(value: object) -> TypeGuard[int | float]:
    if not _is_number(value):
        return False
    return isinstance(value, int) or value.is_integer()


def _is_multiple_of_5(value: object) -> bool:
    return _is_integer(value) and int(value) % 5 == 0


def _is_required_text(value: object) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
    )


def validate(raw: RawWorkbook) -> list[ValidationIssue]:
    """Return every validation issue found. Collects all issues in one
    pass rather than failing fast, so a manager can fix everything in
    one iteration rather than one error at a time."""
    issues: list[ValidationIssue] = []

    # Structural issues surfaced by the loader (missing sheet/header).
    for loader_issue in raw.loader_issues:
        issues.append(ValidationIssue(sheet=loader_issue.sheet, id=None, field=None, message=loader_issue.message))

    # If the workbook is structurally broken, nothing below is safe to check.
    if raw.loader_issues:
        return issues

    issues.extend(_validate_segment_prices(raw))
    issues.extend(_validate_farms(raw))
    issues.extend(_validate_clients(raw))
    issues.extend(_validate_station(raw))

    return issues


def _validate_segment_prices(raw: RawWorkbook) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for seg in ("A", "B", "C", "D"):
        price = raw.segment_prices.get(seg)
        if price is None:
            issues.append(
                ValidationIssue(
                    sheet="Station",
                    id=None,
                    field="reference_export_price_per_t_eur",
                    message=f"Missing segment reference price for segment {seg}",
                )
            )
        elif not _is_integer(price) or price <= 0:
            issues.append(
                ValidationIssue(
                    sheet="Station",
                    id=None,
                    field="reference_export_price_per_t_eur",
                    message=f"Segment {seg} reference price must be a positive integer, found {price!r}",
                )
            )
    return issues


def _validate_farms(raw: RawWorkbook) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()
    mix_fields = ("expected_A_pct", "expected_B_pct", "expected_C_pct", "expected_D_pct")
    actual_fields = ("actual_A_t", "actual_B_t", "actual_C_t", "actual_D_t")

    for row in raw.farms:
        farm_id = row.get("farm_id")
        valid_farm_id = farm_id if _is_required_text(farm_id) else None
        if valid_farm_id is None:
            issues.append(
                ValidationIssue(
                    sheet="Farms",
                    id=None,
                    field="farm_id",
                    message="farm_id must be non-empty text without leading or trailing whitespace",
                )
            )
        else:
            if FARM_ID_PATTERN.fullmatch(valid_farm_id) is None:
                issues.append(
                    ValidationIssue(
                        sheet="Farms",
                        id=valid_farm_id,
                        field="farm_id",
                        message="farm_id must use the format F followed by digits",
                    )
                )
            if valid_farm_id in seen_ids:
                issues.append(ValidationIssue(sheet="Farms", id=valid_farm_id, field="farm_id", message=f"Duplicate farm_id '{valid_farm_id}'"))
            seen_ids.add(valid_farm_id)

        issue_id = valid_farm_id
        name = row.get("farm_name")
        if not _is_required_text(name):
            issues.append(
                ValidationIssue(
                    sheet="Farms",
                    id=issue_id,
                    field="farm_name",
                    message="Farm name must be non-empty text without leading or trailing whitespace",
                )
            )

        cap = row.get("expected_daily_capacity_t")
        if not _is_number(cap):
            issues.append(ValidationIssue(sheet="Farms", id=issue_id, field="expected_daily_capacity_t", message=f"Expected daily capacity must be a finite number, found {cap!r}"))
        elif cap < 0:
            issues.append(ValidationIssue(sheet="Farms", id=issue_id, field="expected_daily_capacity_t", message=f"Expected daily capacity must be non-negative, found {cap}"))

        mix_sum = 0.0
        mix_ok = True
        for field in mix_fields:
            val = row.get(field)
            if not _is_number(val):
                issues.append(ValidationIssue(sheet="Farms", id=issue_id, field=field, message=f"Mix value must be a finite number, found {val!r}"))
                mix_ok = False
                continue
            if val < 0 - TOLERANCE or val > 1 + TOLERANCE:
                issues.append(ValidationIssue(sheet="Farms", id=issue_id, field=field, message=f"Mix value must be between 0 and 1, found {val}"))
                mix_ok = False
            mix_sum += val
        if mix_ok and abs(mix_sum - 1.0) > TOLERANCE:
            issues.append(
                ValidationIssue(
                    sheet="Farms",
                    id=issue_id,
                    field=mix_fields[-1],
                    message=(
                        f"Expected mix for farm {issue_id or '<invalid ID>'} sums to {mix_sum:.2f}, not 1.0 "
                        f"(A={row.get('expected_A_pct')}, B={row.get('expected_B_pct')}, "
                        f"C={row.get('expected_C_pct')}, D={row.get('expected_D_pct')})"
                    ),
                )
            )

        for field in actual_fields:
            val = row.get(field)
            if not _is_integer(val):
                issues.append(ValidationIssue(sheet="Farms", id=issue_id, field=field, message=f"Actual tonnage must be a finite integer, found {val!r}"))
                continue
            if val < 0:
                issues.append(ValidationIssue(sheet="Farms", id=issue_id, field=field, message=f"Actual tonnage must be non-negative, found {val}"))
            elif not _is_multiple_of_5(val):
                issues.append(ValidationIssue(sheet="Farms", id=issue_id, field=field, message=f"Actual tonnage must be a multiple of 5 t, found {val}"))

    return issues


def _validate_clients(raw: RawWorkbook) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_ids: set[str] = set()

    for row in raw.clients:
        client_id = row.get("client_id")
        valid_client_id = client_id if _is_required_text(client_id) else None
        if valid_client_id is None:
            issues.append(
                ValidationIssue(
                    sheet="Clients",
                    id=None,
                    field="client_id",
                    message="client_id must be non-empty text without leading or trailing whitespace",
                )
            )
        else:
            if CLIENT_ID_PATTERN.fullmatch(valid_client_id) is None:
                issues.append(
                    ValidationIssue(
                        sheet="Clients",
                        id=valid_client_id,
                        field="client_id",
                        message="client_id must use the format C followed by digits",
                    )
                )
            if valid_client_id in seen_ids:
                issues.append(ValidationIssue(sheet="Clients", id=valid_client_id, field="client_id", message=f"Duplicate client_id '{valid_client_id}'"))
            seen_ids.add(valid_client_id)

        issue_id = valid_client_id
        name = row.get("client_name")
        if not _is_required_text(name):
            issues.append(
                ValidationIssue(
                    sheet="Clients",
                    id=issue_id,
                    field="client_name",
                    message="Client name must be non-empty text without leading or trailing whitespace",
                )
            )

        mode = row.get("acceptance_mode")
        if not isinstance(mode, str) or mode not in VALID_MODES:
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="acceptance_mode", message=f"Acceptance mode {mode!r} is not valid — expected EXACT or MINIMUM"))

        segment = row.get("requested_segment")
        if not isinstance(segment, str) or segment not in VALID_SEGMENTS:
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="requested_segment", message=f"Requested segment {segment!r} is not valid — expected A, B, C or D"))

        demand = row.get("demand_t")
        if not _is_integer(demand):
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="demand_t", message=f"Demand must be a finite integer, found {demand!r}"))
        elif demand < 0:
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="demand_t", message=f"Demand must be non-negative, found {demand}"))
        elif not _is_multiple_of_5(demand):
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="demand_t", message=f"Demand must be a multiple of 5 t, found {demand}"))

        price = row.get("export_price_per_t_eur")
        if not _is_integer(price):
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="export_price_per_t_eur", message=f"Export price must be a finite integer, found {price!r}"))
        elif price < 0:
            issues.append(ValidationIssue(sheet="Clients", id=issue_id, field="export_price_per_t_eur", message=f"Export price must be non-negative, found {price}"))

    return issues


def _validate_station(raw: RawWorkbook) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    row = raw.station
    if row is None:
        issues.append(ValidationIssue(sheet="Station", id=None, field="station_id", message="Missing station row"))
        return issues

    station_id = row.get("station_id")
    valid_station_id = station_id if _is_required_text(station_id) else None
    if valid_station_id is None:
        issues.append(ValidationIssue(sheet="Station", id=None, field="station_id", message="station_id must be non-empty text without leading or trailing whitespace"))

    capacity = row.get("export_conditioning_capacity_t")
    if not _is_integer(capacity):
        issues.append(ValidationIssue(sheet="Station", id=valid_station_id, field="export_conditioning_capacity_t", message=f"Station capacity must be a finite integer, found {capacity!r}"))
    elif capacity < 0:
        issues.append(ValidationIssue(sheet="Station", id=valid_station_id, field="export_conditioning_capacity_t", message=f"Station capacity must be non-negative, found {capacity}"))
    elif not _is_multiple_of_5(capacity):
        issues.append(ValidationIssue(sheet="Station", id=valid_station_id, field="export_conditioning_capacity_t", message=f"Station capacity must be a multiple of 5 t, found {capacity}"))

    # local_market_ratio is intentionally NOT validated for range — per
    # explicit decision, it is trusted source configuration, used as
    # supplied. Only confirm it is present and numeric so downstream
    # arithmetic doesn't crash.
    ratio = row.get("local_market_ratio")
    if not _is_number(ratio):
        issues.append(ValidationIssue(sheet="Station", id=valid_station_id, field="local_market_ratio", message=f"Local market ratio must be a finite number, found {ratio!r}"))

    return issues


def to_domain(raw: RawWorkbook) -> tuple[list[Farm], list[Client], Station]:
    """Build typed domain objects from raw rows.

    Callers MUST only call this after validate(raw) returned no issues —
    this function assumes well-formed input and does not re-check it.
    """
    farms = [
        Farm(
            farm_id=row["farm_id"],
            name=row["farm_name"],
            expected_capacity_t=float(row["expected_daily_capacity_t"]),
            expected_mix={
                Segment.A: float(row["expected_A_pct"]),
                Segment.B: float(row["expected_B_pct"]),
                Segment.C: float(row["expected_C_pct"]),
                Segment.D: float(row["expected_D_pct"]),
            },
            actual={
                Segment.A: int(row["actual_A_t"]),
                Segment.B: int(row["actual_B_t"]),
                Segment.C: int(row["actual_C_t"]),
                Segment.D: int(row["actual_D_t"]),
            },
        )
        for row in raw.farms
    ]

    clients = [
        Client(
            client_id=row["client_id"],
            name=row["client_name"],
            mode=AcceptanceMode(row["acceptance_mode"]),
            requested_segment=Segment(row["requested_segment"]),
            demand_t=int(row["demand_t"]),
            price_eur=int(row["export_price_per_t_eur"]),
        )
        for row in raw.clients
    ]

    station_row = raw.station
    station = Station(
        station_id=station_row["station_id"],
        capacity_t=int(station_row["export_conditioning_capacity_t"]),
        local_market_ratio=float(station_row["local_market_ratio"]),
        reference_prices={
            Segment(seg): int(price) for seg, price in raw.segment_prices.items()
        },
    )

    return farms, clients, station
