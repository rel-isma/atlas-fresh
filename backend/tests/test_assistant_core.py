"""Tests for the pure assistant core: context.py, guard.py, provider.py.

These do not require FastAPI, Pydantic, or any HTTP layer — they
exercise the assistant's actual grounding logic directly, using the
same real, authoritative workbook the engine tests use. Written with
stdlib unittest for the same reason as test_engine.py (see its
docstring): no network access in this environment to install pytest.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.core.assistant import context as ctx
from app.core.assistant.guard import UngroundedAnswerError, ensure_grounded, known_ids, validate_cited_ids
from app.core.assistant.provider import FallbackProvider
from app.core.engine import allocate
from app.core.loader import load_workbook
from app.core.validation import to_domain, validate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Atlas_Fresh_Production_Commercial_Data.xlsx"


def _baseline_plan():
    raw = load_workbook(DATA_PATH)
    issues = validate(raw)
    assert not issues, f"Baseline workbook failed validation: {issues}"
    farms, clients, station = to_domain(raw)
    return allocate(farms, clients, station)


class TestAssistantAtRiskClients(unittest.TestCase):
    """Business rule: the at-risk-clients answer must cite exactly the
    clients that are actually PARTIAL/UNSERVED in the current
    PlanResult, with their real, documented shortage reasons — never
    invented IDs, never a different set of clients."""

    def test_grounded_citations_match_baseline_at_risk_clients(self):
        plan = _baseline_plan()
        context = ctx.build_context(plan, "at_risk_clients")
        provider = FallbackProvider()
        result = provider.answer("at_risk_clients", context, plan)

        grounded_ids = ensure_grounded(result.cited_ids, plan)
        self.assertEqual(set(grounded_ids), {"C02", "C09", "C08"})
        self.assertIn("C02", result.answer)
        self.assertIn("C09", result.answer)
        self.assertIn("C08", result.answer)


class TestAssistantFarmGaps(unittest.TestCase):
    def test_farm_gaps_cites_real_local_residual_farms(self):
        plan = _baseline_plan()
        context = ctx.build_context(plan, "farm_gaps")
        provider = FallbackProvider()
        result = provider.answer("farm_gaps", context, plan)

        grounded_ids = ensure_grounded(result.cited_ids, plan)
        self.assertEqual(set(grounded_ids), {"F15", "F16", "F19", "F20"})


class TestAssistantLocalResidual(unittest.TestCase):
    def test_local_residual_answer_matches_baseline_value(self):
        plan = _baseline_plan()
        context = ctx.build_context(plan, "local_residual")
        provider = FallbackProvider()
        result = provider.answer("local_residual", context, plan)

        self.assertIn("60", result.answer)
        self.assertIn("4,500", result.answer)
        self.assertNotIn(
            "each tonne was rejected",
            result.answer.lower(),
            "must never imply every local tonne was individually rejected by capacity",
        )


class TestAssistantGuardRejectsUnknownIds(unittest.TestCase):
    """Business rule: the guard must reject/strip any cited ID that
    does not genuinely exist in the current PlanResult. This is the
    mechanism, not just a policy statement."""

    def test_unknown_id_is_stripped_not_shown(self):
        plan = _baseline_plan()
        valid = known_ids(plan)
        self.assertNotIn("C99", valid)
        self.assertNotIn("F99", valid)

        cleaned = validate_cited_ids(["C02", "C99", "F20", "F99"], plan)
        self.assertEqual(set(cleaned), {"C02", "F20"})

    def test_fully_fabricated_citation_list_is_rejected(self):
        plan = _baseline_plan()
        with self.assertRaises(UngroundedAnswerError):
            ensure_grounded(["C99", "F99"], plan)


class TestAssistantUnsupportedQuestion(unittest.TestCase):
    """Business rule: a question that cannot be mapped to one of the
    three supported topics must be treated honestly as unavailable —
    never guessed at, never answered with a fabricated response."""

    def test_free_text_resolves_known_topics(self):
        self.assertEqual(ctx.resolve_question_key("Which clients are at risk?"), "at_risk_clients")
        self.assertEqual(ctx.resolve_question_key("What farm gaps matter today?"), "farm_gaps")
        self.assertEqual(ctx.resolve_question_key("Why did local volume happen?"), "local_residual")

    def test_free_text_unsupported_topic_returns_none(self):
        self.assertIsNone(ctx.resolve_question_key("What's the weather forecast for tomorrow?"))
        self.assertIsNone(ctx.resolve_question_key("Can you book a truck for delivery?"))


if __name__ == "__main__":
    unittest.main()
