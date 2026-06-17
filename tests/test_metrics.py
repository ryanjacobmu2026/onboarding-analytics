"""Tests for the onboarding metrics computation."""

from __future__ import annotations

import unittest
from typing import Optional

from src.config import FUNNEL_STAGES
from src.metrics import compute


def make_dev(plan: str, region: str, stage_index: int,
             latency: Optional[float], calls: int, signup: str) -> dict:
    return {
        "developer_id": "DEV-X",
        "company": "Test Co",
        "plan": plan,
        "region": region,
        "signup_at": signup,
        "reached": list(FUNNEL_STAGES[: stage_index + 1]),
        "furthest_stage": FUNNEL_STAGES[stage_index],
        "activation_latency_hours": latency,
        "api_calls_30d": calls,
        "error_rate": 0.01,
    }


def _fixture() -> list:
    return [
        make_dev("free", "India", 5, 10.0, 1_000, "2026-05-04T09:00:00"),
        make_dev("free", "India", 3, 20.0, 100, "2026-05-05T09:00:00"),
        make_dev("pro", "Europe", 4, 5.0, 5_000, "2026-05-12T09:00:00"),
        make_dev("enterprise", "North America", 5, 2.0, 100_000, "2026-05-13T09:00:00"),
        make_dev("free", "APAC", 0, None, 0, "2026-05-20T09:00:00"),
        make_dev("enterprise", "Europe", 4, 3.0, 50_000, "2026-05-21T09:00:00"),
    ]


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.metrics = compute(_fixture())

    def _count(self, stage: str) -> int:
        return next(r["count"] for r in self.metrics["funnel"] if r["stage"] == stage)

    def test_funnel_counts(self):
        self.assertEqual(self._count("signed_up"), 6)
        self.assertEqual(self._count("activated"), 4)
        self.assertEqual(self._count("integrated"), 2)

    def test_funnel_is_monotonic(self):
        counts = [r["count"] for r in self.metrics["funnel"]]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_activation_rate(self):
        self.assertEqual(self.metrics["kpis"]["activation_rate"], round(4 / 6, 4))

    def test_median_latency(self):
        # latencies present: [10, 20, 5, 2, 3] -> median 5
        self.assertEqual(self.metrics["kpis"]["median_activation_latency_h"], 5.0)

    def test_enterprise_usage_share(self):
        expected = round(150_000 / 156_100, 4)
        self.assertEqual(self.metrics["kpis"]["enterprise_usage_share"], expected)

    def test_plan_segment_activation_rate(self):
        free = next(r for r in self.metrics["segments_by_plan"] if r["plan"] == "free")
        self.assertEqual(free["developers"], 3)
        self.assertEqual(free["activation_rate"], round(1 / 3, 4))

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            compute([])


if __name__ == "__main__":
    unittest.main()
