"""POST /api/assistant

Thin route. Recomputes the same PlanResult /api/plan would produce
(no caching, no persistence — consistent with the rest of the
backend), builds structured context, calls the configured provider
(only FallbackProvider exists in this phase), and validates the
result through the guard before returning it. No allocation logic,
no business calculation, lives here.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..core.assistant import context as ctx
from ..core.assistant.guard import UngroundedAnswerError, ensure_grounded
from ..core.assistant.provider import FallbackProvider, get_default_provider
from ..core.engine import allocate
from ..core.loader import load_workbook
from ..core.validation import to_domain, validate
from .schemas import AssistantAvailableResponse, AssistantRequest, AssistantUnavailableResponse

logger = logging.getLogger(__name__)

router = APIRouter()

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "Atlas_Fresh_Production_Commercial_Data.xlsx"


def _json(body, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=body.model_dump(by_alias=True))


def _load_current_plan():
    """Returns (plan_result, None) on success, or (None, unavailable_response)
    if the plan cannot currently be computed — the assistant must never
    answer from stale or fabricated data."""
    if not DATA_PATH.exists():
        return None, AssistantUnavailableResponse(reason="plan_unavailable", fallback_answer=None)
    try:
        raw = load_workbook(DATA_PATH)
    except Exception:
        logger.exception("Assistant: failed to read workbook")
        return None, AssistantUnavailableResponse(reason="plan_unavailable", fallback_answer=None)

    issues = validate(raw)
    if issues:
        return None, AssistantUnavailableResponse(
            reason="plan_unavailable",
            fallback_answer="Today's plan can't be computed right now because the source data has validation issues.",
        )

    try:
        farms, clients, station = to_domain(raw)
        plan = allocate(farms, clients, station)
    except Exception:
        logger.exception("Assistant: engine failed on validated input")
        return None, AssistantUnavailableResponse(reason="plan_unavailable", fallback_answer=None)

    return plan, None


@router.post("/api/assistant", response_model=None)
def ask_assistant(request: AssistantRequest):
    plan, unavailable = _load_current_plan()
    if unavailable is not None:
        return _json(unavailable)

    # Resolve which of the three supported questions is being asked.
    # 1) An exact structured key ("question": "at_risk_clients", ...).
    # 2) Free text that happens to match the narrow keyword router —
    #    handled the same way as (1): narrow context, works with or
    #    without a real LLM configured.
    # 3) Free text that does NOT match the narrow router, but plausibly
    #    belongs to this domain, AND a real LLM provider is configured
    #    — only in this case do we widen to the full PlanResult and let
    #    the model reason over the raw question. FallbackProvider has
    #    no reasoning to offer here, so this path is skipped entirely
    #    when only the fallback is available (no point building a full
    #    context nothing will use).
    provider = get_default_provider()
    question_key: str | None = None
    built_context: dict | None = None
    question_text: str | None = None

    if request.question in ctx.SUPPORTED_QUESTIONS:
        question_key = request.question
        built_context = ctx.build_context(plan, question_key)
    elif request.free_text:
        question_key = ctx.resolve_question_key(request.free_text)
        if question_key is not None:
            built_context = ctx.build_context(plan, question_key)
        elif not isinstance(provider, FallbackProvider) and ctx.is_plausibly_relevant(request.free_text):
            question_text = request.free_text
            built_context = ctx.build_full_context(plan)

    if built_context is None:
        return _json(
            AssistantUnavailableResponse(
                reason="not_supported_by_current_plan",
                fallback_answer="That's not something today's computed plan can answer.",
            )
        )

    try:
        result = provider.answer(
            question_key=question_key,
            question_text=question_text,
            context=built_context,
            plan=plan,
        )
    except Exception:
        # Honest, labeled failure — never a fabricated answer.
        logger.exception("Assistant provider failed")
        return _json(
            AssistantUnavailableResponse(
                reason="provider_timeout",
                fallback_answer="The assistant couldn't generate an answer just now.",
            )
        )

    # Guard: every cited ID must genuinely exist in this PlanResult.
    try:
        grounded_ids = ensure_grounded(result.cited_ids, plan)
    except UngroundedAnswerError:
        logger.warning("Assistant answer rejected: cited only unknown IDs")
        return _json(
            AssistantUnavailableResponse(
                reason="invalid_output",
                fallback_answer="The assistant's answer couldn't be verified against today's plan, so it isn't shown.",
            )
        )

    return _json(AssistantAvailableResponse(answer=result.answer, cited_ids=grounded_ids, source=result.source))