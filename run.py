#!/usr/bin/env python3
"""One-command launcher: generate data, compute metrics, build dashboard + CSVs.

    python3 run.py             # full pipeline with default 600 developers
    python3 run.py generate    # only generate synthetic data
    python3 run.py build       # only rebuild outputs from existing data
"""

import sys

from src.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["all"]))
