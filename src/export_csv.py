"""Writes the computed metrics out as CSVs for Power BI / Google Sheets import."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from . import config


def _write_rows(path: Path, rows: List[Dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_exports(metrics: Dict, output_dir: Path = config.OUTPUT_DIR) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    kpi_rows = [{"metric": key, "value": value} for key, value in metrics["kpis"].items()]
    tables = {
        "kpis": kpi_rows,
        "funnel": metrics["funnel"],
        "signups_weekly": metrics["signups_weekly"],
        "latency_by_plan": metrics["latency_by_plan"],
        "segments_by_plan": metrics["segments_by_plan"],
        "segments_by_region": metrics["segments_by_region"],
        "cohorts": metrics["cohorts"],
    }

    paths: Dict[str, Path] = {}
    for name, rows in tables.items():
        path = output_dir / f"{name}.csv"
        _write_rows(path, rows)
        paths[name] = path
    return paths
