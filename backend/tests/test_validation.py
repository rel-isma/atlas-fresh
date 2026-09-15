"""Focused tests for workbook values before domain conversion."""

from __future__ import annotations

import math
import unittest

from app.core.loader import RawWorkbook
from app.core.validation import to_domain, validate


def _valid_raw() -> RawWorkbook:
    return RawWorkbook(
        farms=[
            {
                "farm_id": "F01",
                "farm_name": "Farm One",
                "expected_daily_capacity_t": 20.0,
                "expected_A_pct": 1.0,
                "expected_B_pct": 0.0,
                "expected_C_pct": 0.0,
                "expected_D_pct": 0.0,
                "actual_A_t": 20,
                "actual_B_t": 0,
                "actual_C_t": 0,
                "actual_D_t": 0,
            }
        ],
        clients=[
            {
                "client_id": "C01",
                "client_name": "Client One",
                "acceptance_mode": "EXACT",
                "requested_segment": "A",
                "demand_t": 10,
                "export_price_per_t_eur": 1000,
            }
        ],
        station={
            "station_id": "STATION-01",
            "export_conditioning_capacity_t": 20,
            "local_market_ratio": 0.1,
        },
        segment_prices={"A": 1000, "B": 800, "C": 600, "D": 400},
        loader_issues=[],
    )


class TestValidationTypes(unittest.TestCase):
    def test_valid_integral_values_are_converted_without_rounding(self):
        raw = _valid_raw()
        self.assertEqual(validate(raw), [])

        farms, clients, station = to_domain(raw)
        self.assertEqual(farms[0].actual[next(iter(farms[0].actual))], 20)
        self.assertEqual(clients[0].price_eur, 1000)
        self.assertEqual(station.capacity_t, 20)

    def test_ids_and_names_must_be_clean_non_empty_text(self):
        raw = _valid_raw()
        raw.farms[0]["farm_id"] = 101
        raw.farms[0]["farm_name"] = " "
        raw.clients[0]["client_id"] = " C01"
        raw.clients[0]["client_name"] = None
        raw.station["station_id"] = ""

        fields = {issue.field for issue in validate(raw)}
        self.assertTrue(
            {"farm_id", "farm_name", "client_id", "client_name", "station_id"}
            <= fields
        )

    def test_farm_and_client_ids_use_groundable_formats(self):
        raw = _valid_raw()
        raw.farms[0]["farm_id"] = "Farm-1"
        raw.clients[0]["client_id"] = "Client-1"

        messages = [issue.message for issue in validate(raw)]
        self.assertTrue(any("format F" in message for message in messages))
        self.assertTrue(any("format C" in message for message in messages))

    def test_non_finite_and_fractional_integer_fields_are_rejected(self):
        raw = _valid_raw()
        raw.farms[0]["expected_daily_capacity_t"] = math.nan
        raw.farms[0]["actual_A_t"] = 12.5
        raw.clients[0]["demand_t"] = math.inf
        raw.clients[0]["export_price_per_t_eur"] = 999.5
        raw.station["export_conditioning_capacity_t"] = 17.5
        raw.station["local_market_ratio"] = math.inf
        raw.segment_prices["A"] = 1000.5

        fields = [issue.field for issue in validate(raw)]
        self.assertIn("expected_daily_capacity_t", fields)
        self.assertIn("actual_A_t", fields)
        self.assertIn("demand_t", fields)
        self.assertIn("export_price_per_t_eur", fields)
        self.assertIn("export_conditioning_capacity_t", fields)
        self.assertIn("local_market_ratio", fields)
        self.assertIn("reference_export_price_per_t_eur", fields)


if __name__ == "__main__":
    unittest.main()
