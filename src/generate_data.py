"""Generates a realistic synthetic developer-onboarding dataset.

Produces one record per developer capturing how far they got through the API
onboarding funnel, how long activation took, their plan, region and 30-day API
usage. The data is seeded (deterministic) and shaped so that higher tiers
activate faster and use the API more -- the patterns the analytics layer exists
to surface.

Writes:
  data/developers.json   full per-developer records
  data/events.csv        long-format funnel events (one row per stage reached)
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from . import config

_COMPANY_PREFIX = ["Nimbus", "Quark", "Vertex", "Lumen", "Orbit", "Forge", "Pulse",
                   "Atlas", "Cobalt", "Drift", "Helix", "Ember", "Nova", "Sable"]
_COMPANY_SUFFIX = ["Labs", "Systems", "AI", "Cloud", "Works", "Data", "Tech", "Stack"]

# Probability of advancing to the next stage, given the previous was reached.
_P_VERIFIED = 0.90
_P_APIKEY = 0.86
_P_FIRSTCALL = 0.82
_P_ACTIVATED = {"free": 0.62, "pro": 0.80, "enterprise": 0.93}
_P_INTEGRATED = {"free": 0.45, "pro": 0.65, "enterprise": 0.85}

# Activation latency (signup -> first successful call), in hours, by plan.
_LATENCY = {
    "free": (8, 48, 360),
    "pro": (4, 18, 120),
    "enterprise": (1, 6, 36),
}


def _company(rng: random.Random) -> str:
    return f"{rng.choice(_COMPANY_PREFIX)} {rng.choice(_COMPANY_SUFFIX)}"


def _reached_stages(rng: random.Random, plan: str) -> List[str]:
    stages = ["signed_up"]
    ladder = [
        ("verified_email", _P_VERIFIED),
        ("created_api_key", _P_APIKEY),
        ("first_api_call", _P_FIRSTCALL),
        ("activated", _P_ACTIVATED[plan]),
        ("integrated", _P_INTEGRATED[plan]),
    ]
    for stage, probability in ladder:
        if rng.random() <= probability:
            stages.append(stage)
        else:
            break
    return stages


def _activation_latency(rng: random.Random, plan: str) -> float:
    low, mode, high = _LATENCY[plan]
    return round(rng.triangular(low, high, mode), 1)


def _api_calls(rng: random.Random, plan: str, activated: bool, reached_call: bool) -> int:
    if not reached_call:
        return 0
    ranges = {
        ("enterprise", True): (20_000, 300_000),
        ("enterprise", False): (500, 20_000),
        ("pro", True): (2_000, 40_000),
        ("pro", False): (100, 5_000),
        ("free", True): (200, 5_000),
        ("free", False): (0, 500),
    }
    low, high = ranges[(plan, activated)]
    return rng.randint(low, high)


def _stage_event_times(signup: datetime, reached: List[str], latency: Optional[float],
                       rng: random.Random) -> Dict[str, datetime]:
    """Approximate timestamps for each reached stage (for the events export)."""
    times = {"signed_up": signup}
    lat = latency if latency is not None else 4.0
    fractions = {"verified_email": 0.3, "created_api_key": 0.6, "first_api_call": 1.0}
    for stage, frac in fractions.items():
        if stage in reached:
            times[stage] = signup + timedelta(hours=lat * frac)
    if "activated" in reached:
        times["activated"] = times["first_api_call"] + timedelta(hours=rng.uniform(24, 240))
    if "integrated" in reached:
        times["integrated"] = times["activated"] + timedelta(hours=rng.uniform(72, 720))
    return times


def _generate_developer(rng: random.Random, idx: int) -> Dict:
    plan = rng.choices(config.PLANS, weights=config.PLAN_WEIGHTS, k=1)[0]
    region = rng.choices(config.REGIONS, weights=config.REGION_WEIGHTS, k=1)[0]

    # Bias signups toward more recent dates so the dataset shows a growing
    # product (an upward signup trend) rather than a flat one.
    days_ago = int(config.HISTORY_DAYS * (rng.random() ** 1.4))
    signup = datetime.combine(config.REFERENCE_DATE, datetime.min.time()) \
        - timedelta(days=days_ago) \
        + timedelta(hours=rng.randint(0, 23), minutes=rng.randint(0, 59))

    reached = _reached_stages(rng, plan)
    reached_call = "first_api_call" in reached
    activated = "activated" in reached
    latency = _activation_latency(rng, plan) if reached_call else None

    error_rate = round(rng.uniform(0, 0.03 if plan == "enterprise" else 0.08), 3)

    return {
        "developer_id": f"DEV-{idx:04d}",
        "company": _company(rng),
        "plan": plan,
        "region": region,
        "signup_at": signup.isoformat(timespec="seconds"),
        "reached": reached,
        "furthest_stage": reached[-1],
        "activation_latency_hours": latency,
        "api_calls_30d": _api_calls(rng, plan, activated, reached_call),
        "error_rate": error_rate,
        "_event_times": {s: t.isoformat(timespec="seconds")
                         for s, t in _stage_event_times(signup, reached, latency, rng).items()},
    }


def _write_events_csv(developers: List[Dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["developer_id", "plan", "region", "stage", "occurred_at"])
        for dev in developers:
            for stage in dev["reached"]:
                writer.writerow([
                    dev["developer_id"], dev["plan"], dev["region"],
                    stage, dev["_event_times"].get(stage, dev["signup_at"]),
                ])


def generate_dataset(count: int = config.DEFAULT_DEVELOPER_COUNT) -> List[Dict]:
    """Generate ``count`` developer records and write data files. Returns records."""
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")

    rng = random.Random(config.RANDOM_SEED)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    developers = [_generate_developer(rng, idx) for idx in range(1, count + 1)]

    # Strip the internal event-time helper before persisting the clean records.
    clean = [{k: v for k, v in dev.items() if k != "_event_times"} for dev in developers]
    (config.DATA_DIR / "developers.json").write_text(
        json.dumps(clean, indent=2), encoding="utf-8"
    )
    _write_events_csv(developers, str(config.DATA_DIR / "events.csv"))
    return clean
