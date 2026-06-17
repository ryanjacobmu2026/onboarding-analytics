# Power BI / Google Sheets Guide

The platform writes ready-to-import CSV extracts to `output/`. This guide shows
how to turn them into a Power BI report and gives the DAX measures that match
the metrics the Python layer already computes.

> No Power BI? Every metric is already rendered in `output/dashboard.html` —
> just open it in a browser. This guide is for rebuilding it in Power BI.

## The CSV extracts

| File | Grain | Use for |
|------|-------|---------|
| `kpis.csv` | one row per headline metric | KPI cards |
| `funnel.csv` | one row per funnel stage | funnel / waterfall visual |
| `signups_weekly.csv` | one row per ISO week | signups & activations line chart |
| `latency_by_plan.csv` | one row per plan | activation-latency bars |
| `segments_by_plan.csv` | one row per plan | plan breakdown table |
| `segments_by_region.csv` | one row per region | region map / table |
| `cohorts.csv` | one row per weekly cohort | cohort retention matrix |

There is also `data/events.csv` (one row per funnel event, per developer) and
`data/developers.json` if you want to build measures from the raw grain instead
of the pre-aggregated extracts.

## Import into Power BI Desktop (Windows)

1. **Home → Get Data → Text/CSV**, select a file from `output/`. Repeat for each.
2. For `data/events.csv`, set `occurred_at` to a Date/Time type in the Power
   Query editor.
3. Build visuals:
   - **KPI cards** from `kpis.csv` (filter to one `metric` per card).
   - **Funnel visual** using `funnel.csv` → Category = `stage`, Values = `count`.
   - **Line chart** from `signups_weekly.csv` → Axis = `week`, Values =
     `signups` and `activated`.
   - **Clustered bar** from `latency_by_plan.csv` → Axis = `plan`, Values =
     `median_h`, `p90_h`.
   - **Tables** from `segments_by_plan.csv` and `segments_by_region.csv`.
   - **Matrix** from `cohorts.csv` → Rows = `cohort`, Values = `activation_rate`.

## Import into Google Sheets

`File → Import → Upload` each CSV (import to new sheets), then build charts with
`Insert → Chart`. The columns are chart-ready as-is.

## DAX measures (raw-grain version)

If you load `data/developers.json` / `data/events.csv` at the developer grain,
these measures reproduce the headline metrics:

```dax
Total Developers = DISTINCTCOUNT( events[developer_id] )

Activated = CALCULATE( DISTINCTCOUNT( events[developer_id] ),
                       events[stage] = "activated" )

Activation Rate = DIVIDE( [Activated], [Total Developers] )

-- requires a latency column on a developer-grain table
Median Activation Latency (h) = MEDIAN( developers[activation_latency_hours] )

P90 Activation Latency (h) =
    PERCENTILE.INC( developers[activation_latency_hours], 0.90 )

Total API Calls = SUM( developers[api_calls_30d] )

Enterprise Usage Share =
    DIVIDE(
        CALCULATE( [Total API Calls], developers[plan] = "enterprise" ),
        [Total API Calls]
    )

MoM Signup Growth =
VAR ThisMonth = CALCULATE( [Total Developers], DATESMTD( 'Calendar'[Date] ) )
VAR LastMonth =
    CALCULATE( [Total Developers],
        DATEADD( DATESMTD( 'Calendar'[Date] ), -1, MONTH ) )
RETURN DIVIDE( ThisMonth - LastMonth, LastMonth )
```

Step-conversion between funnel stages is easiest as a measure over `funnel.csv`
using `DIVIDE(count, previous count)`, or precomputed in `funnel.csv`'s
`step_conversion` column.
