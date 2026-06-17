"""Command-line entry point for the onboarding analytics platform.

Usage:
    python -m src.cli all                  # generate data, compute, build dashboard + CSVs
    python -m src.cli generate --developers 600
    python -m src.cli build                # rebuild dashboard/CSVs from existing data
"""

from __future__ import annotations

import argparse
import json
from typing import Dict, List, Optional

from . import config
from .dashboard import render
from .export_csv import write_exports
from .generate_data import generate_dataset
from .metrics import compute


def _load_developers() -> List[Dict]:
    path = config.DATA_DIR / "developers.json"
    if not path.exists():
        raise FileNotFoundError("No data found. Run 'generate' (or 'all') first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _print_summary(metrics: Dict) -> None:
    k = metrics["kpis"]
    print("\n" + "=" * 52)
    print("ONBOARDING ANALYTICS SUMMARY")
    print("=" * 52)
    print(f"  Developers tracked      : {metrics['total_developers']}")
    print(f"  Activation rate         : {k['activation_rate'] * 100:.1f}%")
    print(f"  Median time to 1st call : {k['median_activation_latency_h']:.0f}h")
    print(f"  P90 activation latency  : {k['p90_activation_latency_h']:.0f}h")
    print(f"  Enterprise usage share  : {k['enterprise_usage_share'] * 100:.1f}%")
    print(f"  MoM signup growth       : {k['mom_signup_growth'] * 100:+.1f}%")
    print("=" * 52)


def _build(developers: List[Dict]) -> None:
    metrics = compute(developers)
    dashboard_path = config.OUTPUT_DIR / "dashboard.html"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    render(metrics, dashboard_path)
    csv_paths = write_exports(metrics)
    _print_summary(metrics)

    print("\nOutputs written:")
    print(f"  DASHBOARD: {dashboard_path}")
    for name, path in csv_paths.items():
        print(f"  CSV      : {path}")
    print(f"\nOpen the dashboard in your browser:\n  {dashboard_path}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AI API Integration & Onboarding Analytics Platform")
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="generate synthetic onboarding data")
    gen.add_argument("--developers", type=int, default=config.DEFAULT_DEVELOPER_COUNT)

    sub.add_parser("build", help="compute metrics and build dashboard + CSVs from existing data")

    allcmd = sub.add_parser("all", help="generate data, then compute and build everything")
    allcmd.add_argument("--developers", type=int, default=config.DEFAULT_DEVELOPER_COUNT)

    args = parser.parse_args(argv)

    try:
        if args.command == "generate":
            developers = generate_dataset(args.developers)
            print(f"Generated {len(developers)} developers -> {config.DATA_DIR}")
        elif args.command == "build":
            _build(_load_developers())
        elif args.command == "all":
            developers = generate_dataset(args.developers)
            print(f"Generated {len(developers)} developers -> {config.DATA_DIR}")
            _build(developers)
        else:
            parser.print_help()
            return 1
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
