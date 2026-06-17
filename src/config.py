"""Central configuration for the onboarding analytics platform."""

from __future__ import annotations

from datetime import date
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# --- Synthetic data generation ---------------------------------------------
DEFAULT_DEVELOPER_COUNT = 600
RANDOM_SEED = 7
REFERENCE_DATE = date(2026, 6, 15)   # "today" for the dataset
HISTORY_DAYS = 182                   # ~6 months of signups

# The ordered onboarding funnel. Each stage is a strict subset of the one
# before it (a developer can only reach a stage if they reached the previous).
FUNNEL_STAGES = (
    "signed_up",
    "verified_email",
    "created_api_key",
    "first_api_call",
    "activated",        # made enough successful calls to be "activated"
    "integrated",       # shipped to production
)

PLANS = ("free", "pro", "enterprise")
PLAN_WEIGHTS = (0.70, 0.22, 0.08)

REGIONS = ("North America", "Europe", "India", "APAC", "LATAM")
REGION_WEIGHTS = (0.34, 0.26, 0.18, 0.14, 0.08)

# Percentile used for "slow tail" latency reporting.
LATENCY_PERCENTILE = 90
