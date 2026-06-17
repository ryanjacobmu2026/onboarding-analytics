# AI API Integration & Onboarding Analytics Platform

Tracks how developers move through an **API onboarding journey** — from signup
to first API call to activation to production — and surfaces the metrics an API
product team cares about: **funnel conversion, activation latency, cohort
retention and enterprise usage patterns**.

Generates a realistic synthetic dataset, computes the analytics in Python, and
produces a **self-contained interactive HTML dashboard** plus **CSV extracts
ready for Power BI / Google Sheets**.

Pure Python standard library — no install, no API key, opens in any browser.

---

## Quick start (one command)

```bash
cd onboarding-analytics
python3 run.py
```

That generates 600 synthetic developer journeys, computes the metrics, builds
the dashboard, and writes CSV extracts to `output/`. Then open it:

```bash
open output/dashboard.html     # macOS
```

Example run on the included synthetic data:

```
Developers tracked      : 600
Activation rate         : 45.8%   (signup → activated)
Median time to 1st call : 84h     (activation latency)
P90 activation latency  : 223h    (slow tail)
Enterprise usage share  : 77.8%   (of all API calls)
MoM signup growth       : +15.8%
```

## Other commands

```bash
python3 run.py generate --developers 1000   # bigger dataset
python3 run.py build                         # rebuild dashboard/CSVs from existing data
python3 -m unittest discover -s tests        # run the test suite (7 tests)
```

---

## What the dashboard shows

- **KPI cards** — developers tracked, activation rate, median & p90 activation
  latency, enterprise usage share, month-over-month signup growth.
- **Onboarding funnel** — signup → email verified → API key → first call →
  activated → integrated, with step-by-step conversion.
- **Signups & activations over time** — weekly trend (inline SVG line chart).
- **Activation latency by plan** — free vs. pro vs. enterprise.
- **Weekly activation cohorts** — activation rate by signup week.
- **Segment tables** — breakdown by plan and by region (developers, activation
  rate, average API calls, usage share).

## How it works

```
generate_data.py   synthetic developer journeys  →  data/developers.json, data/events.csv
        │
   metrics.py       funnel · latency · cohorts · segments · KPIs
        │
        ├── dashboard.py    →  output/dashboard.html   (interactive, self-contained)
        └── export_csv.py   →  output/*.csv            (Power BI / Sheets ready)
```

Higher tiers are modelled to activate faster and use the API more, and signups
trend upward over time — so the analytics layer has real patterns to surface.

## Power BI

Your resume mentions Power BI. The CSV extracts in `output/` import straight
into Power BI Desktop, and **[POWERBI_GUIDE.md](POWERBI_GUIDE.md)** gives the
exact visuals to build plus the DAX measures that reproduce every metric.

## Project layout

```
onboarding-analytics/
├── run.py                 one-command launcher
├── src/
│   ├── config.py          plans, regions, funnel stages, all settings
│   ├── generate_data.py   synthetic developer-journey generator
│   ├── metrics.py         funnel / latency / cohort / segment analytics
│   ├── dashboard.py       self-contained HTML + inline SVG charts
│   ├── export_csv.py      Power BI / Sheets CSV extracts
│   └── cli.py             command-line entry point
├── tests/                 unittest suite (no pytest needed)
├── POWERBI_GUIDE.md       Power BI import + DAX measures
├── data/                  generated dataset
└── output/                dashboard.html + CSV extracts
```

> All developer data is **synthetic and generated locally**. No real user data
> is used.
