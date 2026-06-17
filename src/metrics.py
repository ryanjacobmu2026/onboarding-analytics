"""Computes onboarding analytics from developer records.

Everything the dashboard and CSV exports need is derived here: funnel
conversion, activation latency, signups over time, plan/region segments,
enterprise usage share and weekly activation cohorts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import mean, median
from typing import Dict, List, Optional, Sequence

from . import config


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
    return round(ordered[rank], 1)


def _week_key(iso_dt: str) -> str:
    day = datetime.fromisoformat(iso_dt).date()
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _month_key(iso_dt: str) -> str:
    return iso_dt[:7]  # "YYYY-MM"


def _funnel(developers: List[Dict]) -> List[Dict]:
    counts = {
        stage: sum(1 for d in developers if stage in d["reached"])
        for stage in config.FUNNEL_STAGES
    }
    signups = counts[config.FUNNEL_STAGES[0]] or 1
    rows: List[Dict] = []
    previous = signups
    for index, stage in enumerate(config.FUNNEL_STAGES):
        count = counts[stage]
        rows.append({
            "stage": stage,
            "count": count,
            "pct_of_signup": round(_safe_div(count, signups), 4),
            "step_conversion": 1.0 if index == 0 else round(_safe_div(count, previous), 4),
        })
        previous = count if count else previous
    return rows


def _latencies(developers: List[Dict]) -> List[float]:
    return [d["activation_latency_hours"] for d in developers
            if d["activation_latency_hours"] is not None]


def _latency_by_plan(developers: List[Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for plan in config.PLANS:
        values = [d["activation_latency_hours"] for d in developers
                  if d["plan"] == plan and d["activation_latency_hours"] is not None]
        rows.append({
            "plan": plan,
            "count": len(values),
            "median_h": round(median(values), 1) if values else 0.0,
            "p90_h": _percentile(values, config.LATENCY_PERCENTILE),
        })
    return rows


def _signups_weekly(developers: List[Dict]) -> List[Dict]:
    signups: Dict[str, int] = defaultdict(int)
    activations: Dict[str, int] = defaultdict(int)
    for dev in developers:
        week = _week_key(dev["signup_at"])
        signups[week] += 1
        if "activated" in dev["reached"]:
            activations[week] += 1
    return [
        {"week": week, "signups": signups[week], "activated": activations[week]}
        for week in sorted(signups)
    ]


def _segment(developers: List[Dict], key: str, buckets: Sequence[str], total_calls: int) -> List[Dict]:
    rows: List[Dict] = []
    for bucket in buckets:
        members = [d for d in developers if d[key] == bucket]
        if not members:
            continue
        activated = sum(1 for d in members if "activated" in d["reached"])
        calls = sum(d["api_calls_30d"] for d in members)
        rows.append({
            key: bucket,
            "developers": len(members),
            "activation_rate": round(_safe_div(activated, len(members)), 4),
            "avg_api_calls": round(_safe_div(calls, len(members)), 0),
            "usage_share": round(_safe_div(calls, total_calls), 4),
        })
    return rows


def _mom_growth(developers: List[Dict]) -> float:
    by_month: Dict[str, int] = defaultdict(int)
    for dev in developers:
        by_month[_month_key(dev["signup_at"])] += 1
    # Exclude the current (partial) month -- comparing a half-elapsed month to a
    # full one would understate growth. Compare the last two *complete* months.
    current_month = config.REFERENCE_DATE.strftime("%Y-%m")
    months = sorted(m for m in by_month if m != current_month)
    if len(months) < 2:
        return 0.0
    last, prev = by_month[months[-1]], by_month[months[-2]]
    return round(_safe_div(last - prev, prev), 4)


def compute(developers: List[Dict]) -> Dict:
    """Return the full metrics payload consumed by the dashboard and exports."""
    if not developers:
        raise ValueError("No developer records to analyse.")

    total = len(developers)
    total_calls = sum(d["api_calls_30d"] for d in developers) or 1
    funnel = _funnel(developers)
    activated = next(r["count"] for r in funnel if r["stage"] == "activated")
    latencies = _latencies(developers)
    enterprise_calls = sum(d["api_calls_30d"] for d in developers if d["plan"] == "enterprise")
    weekly = _signups_weekly(developers)

    return {
        "total_developers": total,
        "kpis": {
            "activation_rate": round(_safe_div(activated, total), 4),
            "median_activation_latency_h": round(median(latencies), 1) if latencies else 0.0,
            "p90_activation_latency_h": _percentile(latencies, config.LATENCY_PERCENTILE),
            "enterprise_usage_share": round(_safe_div(enterprise_calls, total_calls), 4),
            "mom_signup_growth": _mom_growth(developers),
        },
        "funnel": funnel,
        "signups_weekly": weekly,
        "latency_by_plan": _latency_by_plan(developers),
        "segments_by_plan": _segment(developers, "plan", config.PLANS, total_calls),
        "segments_by_region": _segment(developers, "region", config.REGIONS, total_calls),
        "cohorts": [
            {"cohort": row["week"], "size": row["signups"],
             "activation_rate": round(_safe_div(row["activated"], row["signups"]), 4)}
            for row in weekly
        ],
    }
