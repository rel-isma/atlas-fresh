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
        result = provider.answer(question_key="at_risk_clients", question_text=None, context=context, plan=plan)

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
        result = provider.answer(question_key="farm_gaps", question_text=None, context=context, plan=plan)

        grounded_ids = ensure_grounded(result.cited_ids, plan)
        self.assertEqual(set(grounded_ids), {"F15", "F16", "F19", "F20"})


class TestAssistantLocalResidual(unittest.TestCase):
    def test_local_residual_answer_matches_baseline_value(self):
        plan = _baseline_plan()
        context = ctx.build_context(plan, "local_residual")
        provider = FallbackProvider()
        result = provider.answer(question_key="local_residual", question_text=None, context=context, plan=plan)

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

    def test_filter_helper_returns_only_known_ids(self):
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

    def test_any_unknown_id_in_visible_answer_rejects_entire_response(self):
        plan = _baseline_plan()
        with self.assertRaises(UngroundedAnswerError):
            ensure_grounded(
                ["C02"],
                plan,
                answer="C02 is at risk, and fabricated client C999 is also at risk.",
            )

    def test_visible_known_ids_are_included_in_grounded_citations(self):
        plan = _baseline_plan()
        grounded = ensure_grounded([], plan, answer="F15 supplied C02.")
        self.assertEqual(grounded, ["F15", "C02"])


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


class TestAssistantRelevanceGateAndFullContext(unittest.TestCase):
    """Covers the two additions for a real-LLM path: the loose
    relevance gate (used to decide whether to spend an LLM call at
    all on free text the narrow router didn't match) and the full
    PlanResult serializer it would use if it does."""

    def test_relevance_gate_accepts_domain_questions_in_different_phrasing(self):
        # None of these match _FREE_TEXT_KEYWORDS's exact router, but
        # all are genuinely about the domain.
        self.assertTrue(ctx.is_plausibly_relevant("What's driving today's export revenue?"))
        self.assertTrue(ctx.is_plausibly_relevant("How much did station capacity limit us by?"))
        self.assertTrue(ctx.is_plausibly_relevant("Tell me about quality upgrades in today's allocation"))

    def test_relevance_gate_rejects_obviously_unrelated_questions(self):
        self.assertFalse(ctx.is_plausibly_relevant("What's the weather like tomorrow?"))
        self.assertFalse(ctx.is_plausibly_relevant("Can you book a delivery truck?"))
        self.assertFalse(ctx.is_plausibly_relevant("Write me a poem about the ocean"))

    def test_full_context_includes_every_plan_section(self):
        plan = _baseline_plan()
        full = ctx.build_full_context(plan)

        self.assertIn("kpis", full)
        self.assertIn("segment_variances", full)
        self.assertIn("farm_segment_balances", full)
        self.assertIn("client_results", full)
        self.assertIn("allocations", full)
        self.assertIn("local_residual", full)
        self.assertIn("client_status_summary", full)
        self.assertIn("farm_summaries", full)
        self.assertIn("narrative", full)

        # Spot-check it actually carries the real baseline values, not
        # placeholders.
        self.assertEqual(full["kpis"]["export_t"], 500)
        self.assertEqual(full["kpis"]["local_volume_t"], 60)
        client_ids = {c["client_id"] for c in full["client_results"]}
        self.assertEqual(len(client_ids), 10)
        self.assertIn("C02", client_ids)


class TestAssistantMultiSegmentResidual(unittest.TestCase):
    def test_farm_gap_answer_groups_residual_farms_by_segment(self):
        plan = _baseline_plan()
        context = {
            "segment_variances": [
                {
                    "segment": "A",
                    "expected_t": 10.0,
                    "actual_t": 5.0,
                    "variance_t": -5.0,
                }
            ],
            "local_residual_farms": [
                {"farm_id": "F01", "segment": "A", "tonnes_t": 5},
                {"farm_id": "F02", "segment": "B", "tonnes_t": 5},
            ],
        }

        result = FallbackProvider().answer(
            question_key="farm_gaps",
            question_text=None,
            context=context,
            plan=plan,
        )

        self.assertIn("Segment A: F01", result.answer)
        self.assertIn("Segment B: F02", result.answer)


if __name__ == "__main__":
    unittest.main()
