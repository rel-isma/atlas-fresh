"""API schema contract tests that do not require TestClient."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.api.schemas import AssistantRequest, AssistantUnavailableResponse
from app.main import app


class TestAssistantRequestSchema(unittest.TestCase):
    def test_free_text_is_trimmed_and_limited(self):
        request = AssistantRequest(freeText="  What is at risk?  ")
        self.assertEqual(request.free_text, "What is at risk?")

        with self.assertRaises(ValidationError):
            AssistantRequest(freeText="x" * 1001)

    def test_extra_or_ambiguous_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            AssistantRequest(
                question="at_risk_clients",
                freeText="Also inspect farms",
            )
        with self.assertRaises(ValidationError):
            AssistantRequest(question="at_risk_clients", unexpected=True)

    def test_unavailable_response_serializes_nullable_fallback(self):
        body = AssistantUnavailableResponse(reason="plan_unavailable").model_dump(
            by_alias=True
        )
        self.assertIn("fallbackAnswer", body)
        self.assertIsNone(body["fallbackAnswer"])


class TestOpenApiContract(unittest.TestCase):
    def test_success_responses_have_models(self):
        schema = app.openapi()
        plan_response = schema["paths"]["/api/plan"]["get"]["responses"]["200"]
        assistant_response = schema["paths"]["/api/assistant"]["post"][
            "responses"
        ]["200"]

        self.assertEqual(
            plan_response["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/PlanResultSchema",
        )
        self.assertEqual(
            len(
                assistant_response["content"]["application/json"]["schema"][
                    "anyOf"
                ]
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
