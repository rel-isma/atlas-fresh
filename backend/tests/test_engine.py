"""Automated tests for the Atlas Fresh planning engine.

Written with the standard-library `unittest` module so they run with
zero extra dependencies. `unittest.TestCase` classes are natively
discoverable by pytest as well, so `pytest backend/tests` works
unchanged once pytest is available in an environment with network
access — nothing here is unittest-specific by design choice, only by
necessity of this sandbox.

Tests 1-3 use small synthetic fixtures to isolate one ordering/
compatibility rule at a time, independent of the real workbook's
specific shape (which never happens to exercise every rule, e.g. it
has no price tie between any two clients). Tests 4-6 run the real,
authoritative workbook end to end and check the results against the
publicly documented baseline.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.core.engine import allocate
from app.core.loader import load_workbook
from app.core.models import (
    AcceptanceMode,
    ClientStatus,
    Farm,
    Client,
    Segment,
    ShortageReason,
    Station,
)
from app.core.validation import to_domain, validate

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "Atlas_Fresh_Production_Commercial_Data.xlsx"


def _load_baseline():
    raw = load_workbook(DATA_PATH)
    issues = validate(raw)
    assert not issues, f"Baseline workbook failed validation: {issues}"
    return to_domain(raw)


def _find_client(results, client_id):
    return next(c for c in results if c.client_id == client_id)


class TestClientOrdering(unittest.TestCase):
    """Business rule: process clients by export price descending;
    ties are broken by client_id ascending. No other key is used.

    The real workbook has no price tie between any two clients, so this
    rule is only fully exercised with a synthetic fixture.
    """

    def test_client_ordering_price_desc_then_id(self):
        station = Station(
            station_id="STATION-01",
            capacity_t=100,
            local_market_ratio=0.1,
            reference_prices={Segment.A: 1000, Segment.B: 800, Segment.C: 600, Segment.D: 400},
        )
        farms = [
            Farm(
                farm_id="F01",
                name="Farm 1",
                expected_capacity_t=20,
                expected_mix={Segment.A: 1.0, Segment.B: 0, Segment.C: 0, Segment.D: 0},
                actual={Segment.A: 10, Segment.B: 0, Segment.C: 0, Segment.D: 0},
            )
        ]
        # Two clients, EQUAL price, different IDs: the lower client_id
        # must be processed first and therefore win the scarce 10t of
        # supply.
        clients = [
            Client(client_id="C02", name="Second", mode=AcceptanceMode.EXACT, requested_segment=Segment.A, demand_t=10, price_eur=1000),
            Client(client_id="C01", name="First", mode=AcceptanceMode.EXACT, requested_segment=Segment.A, demand_t=10, price_eur=1000),
        ]

        result = allocate(farms, clients, station)

        c01 = _find_client(result.client_results, "C01")
        c02 = _find_client(result.client_results, "C02")
        self.assertEqual(c01.status, ClientStatus.COMPLETE, "Lower client_id must win an equal-price tie")
        self.assertEqual(c02.status, ClientStatus.UNSERVED, "Higher client_id must lose an equal-price tie")


class TestCompatibility(unittest.TestCase):
    """Business rule: EXACT accepts only the requested segment; MINIMUM
    accepts the requested segment or anything better (A > B > C > D)."""

    def _station(self):
        return Station(
            station_id="STATION-01",
            capacity_t=100,
            local_market_ratio=0.1,
            reference_prices={Segment.A: 1000, Segment.B: 800, Segment.C: 600, Segment.D: 400},
        )

    def _farms(self):
        return [
            Farm(
                farm_id="F01",
                name="Farm 1",
                expected_capacity_t=30,
                expected_mix={Segment.A: 0.34, Segment.B: 0.33, Segment.C: 0.33, Segment.D: 0},
                actual={Segment.A: 10, Segment.B: 10, Segment.C: 10, Segment.D: 0},
            )
        ]

    def test_exact_vs_minimum_compatibility(self):
        station = self._station()
        farms = self._farms()

        exact_client = Client(client_id="C01", name="Exact-B", mode=AcceptanceMode.EXACT, requested_segment=Segment.B, demand_t=25, price_eur=800)
        result_exact = allocate(farms, [exact_client], station)
        exact_allocs = result_exact.allocations
        self.assertTrue(all(a.segment == Segment.B for a in exact_allocs), "EXACT client must never receive a non-requested segment")
        self.assertEqual(sum(a.tonnes for a in exact_allocs), 10, "EXACT client can only draw from the 10t of B supply, never A or C")

        minimum_client = Client(client_id="C02", name="Minimum-B", mode=AcceptanceMode.MINIMUM, requested_segment=Segment.B, demand_t=25, price_eur=800)
        result_min = allocate(farms, [minimum_client], station)
        min_allocs = result_min.allocations
        self.assertTrue(all(a.segment in (Segment.A, Segment.B) for a in min_allocs), "MINIMUM-B must accept B or A only, never C")
        self.assertEqual(sum(a.tonnes for a in min_allocs), 20, "MINIMUM-B should draw all compatible A+B supply (10+10)")


class TestCandidateOrdering(unittest.TestCase):
    """Business rule: compatible supply is sorted by smallest quality
    upgrade first, then farm_id. An exact-match segment must be
    exhausted before a "better" segment is touched, even if the better
    segment sits on a farm with a lower ID."""

    def test_candidate_ordering_smallest_upgrade_then_farm_id(self):
        station = Station(
            station_id="STATION-01",
            capacity_t=100,
            local_market_ratio=0.1,
            reference_prices={Segment.A: 1000, Segment.B: 800, Segment.C: 600, Segment.D: 400},
        )
        # F01 (lower id) only has B (an upgrade for a MINIMUM-C request);
        # F02 and F03 (higher ids) have the exact-match C.
        farms = [
            Farm(farm_id="F01", name="F1", expected_capacity_t=10, expected_mix={Segment.A: 0, Segment.B: 1.0, Segment.C: 0, Segment.D: 0}, actual={Segment.A: 0, Segment.B: 10, Segment.C: 0, Segment.D: 0}),
            Farm(farm_id="F02", name="F2", expected_capacity_t=10, expected_mix={Segment.A: 0, Segment.B: 0, Segment.C: 1.0, Segment.D: 0}, actual={Segment.A: 0, Segment.B: 0, Segment.C: 5, Segment.D: 0}),
            Farm(farm_id="F03", name="F3", expected_capacity_t=10, expected_mix={Segment.A: 0, Segment.B: 0, Segment.C: 1.0, Segment.D: 0}, actual={Segment.A: 0, Segment.B: 0, Segment.C: 5, Segment.D: 0}),
        ]
        client = Client(client_id="C01", name="Minimum-C", mode=AcceptanceMode.MINIMUM, requested_segment=Segment.C, demand_t=15, price_eur=600)

        result = allocate(farms, [client], station)

        ordered = result.allocations  # in allocation order
        self.assertEqual(
            [(a.farm_id, a.segment, a.tonnes) for a in ordered],
            [("F02", Segment.C, 5), ("F03", Segment.C, 5), ("F01", Segment.B, 5)],
            "Exact-match C supply (F02, F03, farm_id order) must be exhausted before "
            "the upgraded B supply on F01 is touched, even though F01 has the lowest farm_id overall",
        )


class TestStationCapacityHardLimit(unittest.TestCase):
    """Business rule: exported tonnes can never exceed station capacity;
    once capacity is exhausted, later clients (in price order) get
    STATION_CAPACITY_REACHED. Verified against the real, authoritative
    workbook and the published acceptance-checklist case for C08."""

    def test_station_capacity_hard_limit(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        total_exported = sum(a.tonnes for a in result.allocations)
        self.assertLessEqual(total_exported, station.capacity_t)
        self.assertEqual(total_exported, 500)

        c08 = _find_client(result.client_results, "C08")
        self.assertEqual(c08.status, ClientStatus.PARTIAL)
        self.assertEqual(c08.reason, ShortageReason.STATION_CAPACITY_REACHED)


class TestLocalResidualAndConservation(unittest.TestCase):
    """Business rule: every actual tonne not exported goes local, valued
    at local_market_ratio x reference price. Conservation must hold
    exactly: exported + local == actual received. Verified against the
    real workbook, where the residual is confirmed to be entirely
    Segment D across four specific farms."""

    def test_local_residual_and_conservation(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        total_actual = sum(sum(f.actual.values()) for f in farms)
        total_exported = sum(a.tonnes for a in result.allocations)
        total_local = sum(r.tonnes_t for r in result.local_residual)

        self.assertEqual(total_exported + total_local, total_actual, "Conservation: export + local must equal actual received")
        self.assertEqual(total_local, 60)
        self.assertAlmostEqual(sum(r.local_value_eur for r in result.local_residual), 4500)

        self.assertTrue(all(r.segment == Segment.D for r in result.local_residual), "Baseline residual is verified to be entirely Segment D")
        residual_by_farm = {r.farm_id: r.tonnes_t for r in result.local_residual}
        self.assertEqual(residual_by_farm, {"F15": 5, "F16": 20, "F19": 5, "F20": 30})


class TestFullBaselineReproduction(unittest.TestCase):
    """Verifies that the implemented policy reproduces the authoritative
    baseline end-to-end. Combined with the synthetic rule tests and
    invariants, it provides confidence that the implementation follows
    the documented policy rather than merely matching one displayed KPI.
    """

    def test_full_baseline_reproduction(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)
        k = result.kpis

        self.assertEqual(k.expected_plan_t, 600.0)
        self.assertEqual(k.actual_received_t, 560.0)
        self.assertEqual(k.station_capacity_t, 500)
        self.assertEqual(k.actual_by_segment[Segment.A], 90)
        self.assertEqual(k.actual_by_segment[Segment.B], 160)
        self.assertEqual(k.actual_by_segment[Segment.C], 180)
        self.assertEqual(k.actual_by_segment[Segment.D], 130)
        self.assertEqual(k.export_t, 500)
        self.assertAlmostEqual(k.export_rate, 0.893, delta=0.0005)
        self.assertEqual(k.local_volume_t, 60)
        self.assertEqual(k.export_revenue_eur, 549_500)
        self.assertAlmostEqual(k.local_value_eur, 4_500)
        self.assertAlmostEqual(k.total_value_eur, 554_000)
        self.assertEqual(k.at_risk_client_count, 3)

        c02 = _find_client(result.client_results, "C02")
        c09 = _find_client(result.client_results, "C09")
        c08 = _find_client(result.client_results, "C08")
        self.assertEqual((c02.status, c02.reason), (ClientStatus.PARTIAL, ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT))
        self.assertEqual((c09.status, c09.reason), (ClientStatus.PARTIAL, ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT))
        self.assertEqual((c08.status, c08.reason), (ClientStatus.PARTIAL, ShortageReason.STATION_CAPACITY_REACHED))

        # Spot-check one representative aggregate (not every allocation
        # row — see Phase 5 rationale on avoiding over-specified,
        # implementation-detail-locking tests).
        c01 = _find_client(result.client_results, "C01")
        self.assertEqual((c01.status, c01.allocated_t, c01.revenue_eur), (ClientStatus.COMPLETE, 50, 75_000))


class TestFarmSegmentVariance(unittest.TestCase):
    """Business rule: farm_segment_balances now carries expected_t and
    variance_t per farm/segment, using the same already-approved
    "expected = capacity x mix" formula previously only exposed in
    aggregate (segment_variances). Verified against the real workbook
    and independently cross-checked against a reference UI mockup
    built from the same data (F18: B expected 22.4t/actual 10t =
    -12.4 variance; C expected 9.6t/actual 15t = +5.4 variance)."""

    def test_farm_segment_variance_matches_reference(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        f18_rows = {b.segment: b for b in result.farm_segment_balances if b.farm_id == "F18"}
        self.assertAlmostEqual(f18_rows[Segment.B].expected_t, 22.4, places=2)
        self.assertAlmostEqual(f18_rows[Segment.B].variance_t, -12.4, places=2)
        self.assertAlmostEqual(f18_rows[Segment.C].expected_t, 9.6, places=2)
        self.assertAlmostEqual(f18_rows[Segment.C].variance_t, 5.4, places=2)

    def test_variance_equals_actual_minus_expected_for_every_row(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        for b in result.farm_segment_balances:
            self.assertAlmostEqual(b.variance_t, b.actual_t - b.expected_t, places=6)

    def test_aggregate_segment_variances_still_present_and_unaffected(self):
        """Confirms this change is additive: the aggregate 4-row
        segment_variances (used by Overview's chart) is untouched."""
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        self.assertEqual(len(result.segment_variances), 4)
        segments = {v.segment for v in result.segment_variances}
        self.assertEqual(segments, {Segment.A, Segment.B, Segment.C, Segment.D})


class TestCanonicalSummariesAndNarrative(unittest.TestCase):
    def test_client_and_farm_summaries_are_computed_by_engine(self):
        farms, clients, station = _load_baseline()
        result = allocate(farms, clients, station)

        summary = result.client_status_summary
        self.assertEqual(
            (
                summary.client_count,
                summary.complete_count,
                summary.partial_count,
                summary.unserved_count,
            ),
            (10, 7, 3, 0),
        )
        self.assertEqual(
            (
                summary.complete_pct,
                summary.partial_pct,
                summary.unserved_pct,
                summary.partial_end_pct,
            ),
            (70.0, 30.0, 0.0, 100.0),
        )
        self.assertEqual(
            result.farm_summaries,
            sorted(
                result.farm_summaries,
                key=lambda farm: farm.variance_t,
            ),
        )

    def test_local_ratio_in_narrative_uses_station_configuration(self):
        farm = Farm(
            farm_id="F01",
            name="Farm One",
            expected_capacity_t=10,
            expected_mix={
                Segment.A: 1.0,
                Segment.B: 0,
                Segment.C: 0,
                Segment.D: 0,
            },
            actual={
                Segment.A: 10,
                Segment.B: 0,
                Segment.C: 0,
                Segment.D: 0,
            },
        )
        station = Station(
            station_id="STATION-01",
            capacity_t=0,
            local_market_ratio=0.2,
            reference_prices={
                Segment.A: 1000,
                Segment.B: 800,
                Segment.C: 600,
                Segment.D: 400,
            },
        )

        result = allocate([farm], [], station)

        self.assertIn("20% of reference price", result.narrative.local_residual)
        self.assertNotIn("10% of reference price", result.narrative.local_residual)


if __name__ == "__main__":
    unittest.main()
