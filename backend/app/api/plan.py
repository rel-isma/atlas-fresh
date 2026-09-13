"""GET /api/plan

Thin route. All business logic lives in app.core; this module's only
job is: locate the workbook, call the existing pure functions in the
documented order, and translate the result to JSON via the Pydantic
schemas. No allocation, KPI, status, or residual math happens here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..core.engine import allocate
from ..core.loader import load_workbook
from ..core.validation import to_domain, validate
from .schemas import InvalidPlanResponse, PlanResultSchema, ValidationIssueSchema

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "Atlas_Fresh_Production_Commercial_Data.xlsx"


@router.get("/api/plan", response_model=None)
def get_plan():
    # 1. Locate + load the authoritative, read-only workbook.
    if not DATA_PATH.exists():
        # Infrastructure failure, not a business validation issue —
        # must never be represented as a successful (or even a 422
        # "invalid data") planning result.
        logger.error("Seed workbook not found at %s", DATA_PATH)
        raise HTTPException(status_code=500, detail="The planning workbook could not be found on the server.")

    try:
        raw = load_workbook(DATA_PATH)
    except Exception:
        logger.exception("Failed to read the workbook")
        raise HTTPException(status_code=500, detail="The planning workbook could not be read.")

    # 2. Validate. Never silently repair invalid data.
    issues = validate(raw)
    if issues:
        body = InvalidPlanResponse(
            validation_errors=[ValidationIssueSchema.from_domain(i) for i in issues],
        )
        # Explicit 422 status — returning a Pydantic model directly
        # from a plain route defaults to HTTP 200 regardless of
        # content, so the status code must be set explicitly here.
        return JSONResponse(status_code=422, content=body.model_dump(by_alias=True))

    # 3. Convert to domain objects, then run the deterministic engine.
    try:
        farms, clients, station = to_domain(raw)
        plan_result = allocate(farms, clients, station)
    except Exception:
        # Should not happen if validation passed, but a server error
        # here must still surface honestly, never as fabricated data.
        logger.exception("Planning engine failed on validated input")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while computing the plan.")

    # 4. Serialize. Explicit by_alias=True so JSON is always camelCase
    # regardless of FastAPI/Pydantic version defaults for implicit
    # model return serialization.
    body = PlanResultSchema.from_domain(plan_result)
    return JSONResponse(status_code=200, content=body.model_dump(by_alias=True))
