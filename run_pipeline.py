"""Command-line entry point.

Usage:
    python run_pipeline.py
    python run_pipeline.py --input data/raw/support_tickets_raw.csv --output-dir data/processed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ticket_pipeline import PipelineError, clean, inspect, load_csv
from ticket_pipeline.report import export, summarize

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean the support-ticket CSV and write a report.")
    parser.add_argument("--input", default=ROOT / "data" / "raw" / "support_tickets_raw.csv", type=Path)
    parser.add_argument("--output-dir", default=ROOT / "data" / "processed", type=Path)
    args = parser.parse_args(argv)

    try:
        raw = load_csv(args.input)
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    inspection = inspect(raw)
    result = clean(raw)
    summary = summarize(result, inspection)
    written = export(result, summary, args.output_dir)

    s = result.stats
    print(
        f"Read {s['input_rows']} rows | removed {s['exact_duplicates_removed']} exact duplicates | "
        f"rejected {s['rejected_rows']} | clean {s['clean_rows']}"
    )
    for path in written:
        print(f"  wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
