"""Renders the metrics into a single self-contained, interactive HTML dashboard.

No external libraries or CDNs: charts are hand-rendered as inline SVG / CSS so
the file opens in any browser, offline, by double-clicking it.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from . import config

_INDIGO = "#3b5bdb"
_TEAL = "#0c8599"
_PLAN_COLOURS = {"free": "#868e96", "pro": "#3b5bdb", "enterprise": "#f08c00"}


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _pretty(stage: str) -> str:
    return stage.replace("_", " ").title()


def _kpi_card(label: str, value: str, sub: str = "", accent: str = "#1d1d1f") -> str:
    sub_html = f'<div class="kpi-sub">{html.escape(sub)}</div>' if sub else ""
    return (
        f'<div class="card"><div class="kpi" style="color:{accent}">{html.escape(value)}</div>'
        f'<div class="kpi-label">{html.escape(label)}</div>{sub_html}</div>'
    )


def _funnel_rows(funnel: List[Dict]) -> str:
    rows = []
    for index, step in enumerate(funnel):
        width = step["pct_of_signup"] * 100
        conv = "" if index == 0 else f'<span class="conv">↳ {_pct(step["step_conversion"])} of previous</span>'
        rows.append(
            f'<div class="funnel-row">'
            f'<span class="funnel-label">{_pretty(step["stage"])}</span>'
            f'<span class="funnel-track"><span class="funnel-fill" style="width:{width:.1f}%"></span></span>'
            f'<span class="funnel-val">{step["count"]} &middot; {_pct(step["pct_of_signup"])}</span>'
            f'{conv}</div>'
        )
    return "".join(rows)


def _svg_timeseries(weekly: List[Dict]) -> str:
    if not weekly:
        return '<p class="muted">No signup history.</p>'

    vb_w, vb_h = 920, 280
    left, right, top, bottom = 44, 16, 20, 42
    plot_w, plot_h = vb_w - left - right, vb_h - top - bottom
    n = len(weekly)
    max_val = max(max(w["signups"] for w in weekly), 1)

    def x(i: int) -> float:
        return left if n == 1 else left + plot_w * i / (n - 1)

    def y(v: float) -> float:
        return top + plot_h * (1 - v / max_val)

    def points(field: str) -> str:
        return " ".join(f"{x(i):.1f},{y(w[field]):.1f}" for i, w in enumerate(weekly))

    # horizontal gridlines + y labels
    grid = []
    for frac in (0, 0.5, 1.0):
        gy = top + plot_h * (1 - frac)
        grid.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{vb_w - right}" y2="{gy:.1f}" class="grid"/>')
        grid.append(f'<text x="{left - 8}" y="{gy + 4:.1f}" class="ylab">{int(max_val * frac)}</text>')

    # x labels (~6 evenly spaced)
    step = max(1, n // 6)
    xlabels = [
        f'<text x="{x(i):.1f}" y="{vb_h - 14}" class="xlab">{html.escape(w["week"])}</text>'
        for i, w in enumerate(weekly) if i % step == 0
    ]

    dots = []
    for i, w in enumerate(weekly):
        dots.append(
            f'<circle cx="{x(i):.1f}" cy="{y(w["signups"]):.1f}" r="3" fill="{_INDIGO}">'
            f'<title>{html.escape(w["week"])}: {w["signups"]} signups, {w["activated"]} activated</title></circle>'
        )

    return f'''<svg viewBox="0 0 {vb_w} {vb_h}" class="chart" role="img" aria-label="Signups over time">
      {''.join(grid)}
      <polyline points="{points('signups')}" fill="none" stroke="{_INDIGO}" stroke-width="2.5"/>
      <polyline points="{points('activated')}" fill="none" stroke="{_TEAL}" stroke-width="2" stroke-dasharray="5 4"/>
      {''.join(dots)}
      {''.join(xlabels)}
    </svg>
    <div class="legend"><span class="dot" style="background:{_INDIGO}"></span>Signups
      <span class="dot" style="background:{_TEAL}; margin-left:18px"></span>Activated</div>'''


def _latency_bars(latency_by_plan: List[Dict]) -> str:
    max_median = max((r["median_h"] for r in latency_by_plan), default=1) or 1
    rows = []
    for r in latency_by_plan:
        width = r["median_h"] / max_median * 100
        colour = _PLAN_COLOURS.get(r["plan"], _INDIGO)
        rows.append(
            f'<div class="bar-row"><span class="bar-label">{_pretty(r["plan"])}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{width:.1f}%;background:{colour}"></span></span>'
            f'<span class="bar-val">{r["median_h"]:.0f}h median &middot; {r["p90_h"]:.0f}h p90</span></div>'
        )
    return "".join(rows)


def _segment_table(rows: List[Dict], key: str) -> str:
    body = []
    for r in rows:
        share_bar = (
            f'<span class="mini-track"><span class="mini-fill" '
            f'style="width:{r["usage_share"] * 100:.1f}%"></span></span>' if "usage_share" in r else ""
        )
        share = _pct(r["usage_share"]) if "usage_share" in r else "—"
        body.append(
            f'<tr><td>{html.escape(_pretty(str(r[key])))}</td>'
            f'<td style="text-align:right">{r["developers"]}</td>'
            f'<td style="text-align:right">{_pct(r["activation_rate"])}</td>'
            f'<td style="text-align:right">{int(r["avg_api_calls"]):,}</td>'
            f'<td>{share_bar}{share}</td></tr>'
        )
    return "".join(body)


def _cohort_table(cohorts: List[Dict], limit: int = 12) -> str:
    body = []
    for r in cohorts[-limit:]:
        width = r["activation_rate"] * 100
        body.append(
            f'<tr><td>{html.escape(r["cohort"])}</td>'
            f'<td style="text-align:right">{r["size"]}</td>'
            f'<td><span class="mini-track"><span class="mini-fill" style="width:{width:.1f}%"></span></span>'
            f'{_pct(r["activation_rate"])}</td></tr>'
        )
    return "".join(body)


def render(metrics: Dict, path: Path) -> None:
    k = metrics["kpis"]
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    growth = k["mom_signup_growth"]
    growth_txt = f'{"+" if growth >= 0 else ""}{growth * 100:.1f}%'
    growth_colour = "#1a7f5a" if growth >= 0 else "#b3261e"

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>API Onboarding Analytics</title>
<style>
  :root {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }}
  body {{ margin: 0; background: #f4f5f7; color: #1d1d1f; }}
  header {{ background: linear-gradient(120deg, #1c2333, #2b3a67); color: #fff; padding: 30px 40px; }}
  header h1 {{ margin: 0; font-size: 22px; letter-spacing: -0.2px; }}
  header p {{ margin: 6px 0 0; color: #aeb6c7; font-size: 13px; }}
  main {{ max-width: 1060px; margin: 0 auto; padding: 26px 24px 64px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }}
  .card {{ background: #fff; border: 1px solid #e6e8eb; border-radius: 12px; padding: 18px; }}
  .kpi {{ font-size: 28px; font-weight: 650; }}
  .kpi-label {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  .kpi-sub {{ font-size: 11px; color: #9aa1ab; margin-top: 2px; }}
  section {{ background: #fff; border: 1px solid #e6e8eb; border-radius: 12px; padding: 22px; margin-top: 22px; }}
  section h2 {{ margin: 0 0 16px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; color: #6b7280; }}
  .funnel-row {{ display: grid; grid-template-columns: 130px 1fr 150px; align-items: center; gap: 12px;
                 margin: 7px 0; font-size: 13px; }}
  .funnel-label {{ color: #374151; font-weight: 500; }}
  .funnel-track {{ background: #eef0f2; border-radius: 6px; height: 20px; overflow: hidden; }}
  .funnel-fill {{ display: block; height: 100%; background: linear-gradient(90deg, #3b5bdb, #5c7cfa); }}
  .funnel-val {{ color: #6b7280; text-align: right; }}
  .conv {{ grid-column: 2 / 3; font-size: 11px; color: #9aa1ab; }}
  .bar-row {{ display: flex; align-items: center; gap: 12px; margin: 8px 0; font-size: 13px; }}
  .bar-label {{ width: 110px; color: #374151; }}
  .bar-track {{ flex: 1; background: #eef0f2; border-radius: 6px; height: 16px; overflow: hidden; }}
  .bar-fill {{ display: block; height: 100%; }}
  .bar-val {{ width: 200px; text-align: right; color: #6b7280; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 10px; border-bottom: 1px solid #eef0f2; text-align: left; }}
  th {{ color: #6b7280; font-weight: 600; }}
  .mini-track {{ display: inline-block; width: 90px; height: 8px; background: #eef0f2; border-radius: 4px;
                 overflow: hidden; vertical-align: middle; margin-right: 8px; }}
  .mini-fill {{ display: block; height: 100%; background: #3b5bdb; }}
  .chart {{ width: 100%; height: auto; }}
  .grid-line, .grid {{ stroke: #eef0f2; stroke-width: 1; }}
  .ylab {{ fill: #9aa1ab; font-size: 11px; text-anchor: end; }}
  .xlab {{ fill: #9aa1ab; font-size: 10px; text-anchor: middle; }}
  .legend {{ font-size: 12px; color: #6b7280; margin-top: 8px; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
  .muted {{ color: #9aa1ab; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }}
  @media (max-width: 760px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>AI API Integration &amp; Onboarding Analytics</h1>
  <p>Generated {generated} &nbsp;·&nbsp; {metrics["total_developers"]} developers tracked across the onboarding funnel</p>
</header>
<main>
  <div class="grid">
    {_kpi_card("Developers tracked", str(metrics["total_developers"]))}
    {_kpi_card("Activation rate", _pct(k["activation_rate"]), "signup → activated", _INDIGO)}
    {_kpi_card("Median time to first call", f'{k["median_activation_latency_h"]:.0f}h', "activation latency", _TEAL)}
    {_kpi_card("P90 activation latency", f'{k["p90_activation_latency_h"]:.0f}h', "slow tail")}
    {_kpi_card("Enterprise usage share", _pct(k["enterprise_usage_share"]), "of all API calls", _PLAN_COLOURS["enterprise"])}
    {_kpi_card("MoM signup growth", growth_txt, "latest vs prior month", growth_colour)}
  </div>

  <section>
    <h2>Onboarding funnel</h2>
    {_funnel_rows(metrics["funnel"])}
  </section>

  <section>
    <h2>Signups &amp; activations over time (weekly)</h2>
    {_svg_timeseries(metrics["signups_weekly"])}
  </section>

  <div class="two-col">
    <section>
      <h2>Activation latency by plan</h2>
      {_latency_bars(metrics["latency_by_plan"])}
    </section>
    <section>
      <h2>Weekly activation cohorts</h2>
      <table>
        <thead><tr><th>Cohort</th><th style="text-align:right">Size</th><th>Activation rate</th></tr></thead>
        <tbody>{_cohort_table(metrics["cohorts"])}</tbody>
      </table>
    </section>
  </div>

  <section>
    <h2>By plan</h2>
    <table>
      <thead><tr><th>Plan</th><th style="text-align:right">Developers</th><th style="text-align:right">Activation</th>
      <th style="text-align:right">Avg API calls (30d)</th><th>Usage share</th></tr></thead>
      <tbody>{_segment_table(metrics["segments_by_plan"], "plan")}</tbody>
    </table>
  </section>

  <section>
    <h2>By region</h2>
    <table>
      <thead><tr><th>Region</th><th style="text-align:right">Developers</th><th style="text-align:right">Activation</th>
      <th style="text-align:right">Avg API calls (30d)</th><th>Usage share</th></tr></thead>
      <tbody>{_segment_table(metrics["segments_by_region"], "region")}</tbody>
    </table>
  </section>
</main>
</body>
</html>"""
    path.write_text(document, encoding="utf-8")
