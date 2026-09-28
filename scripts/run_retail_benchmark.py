#!/usr/bin/env python3
"""Run the deterministic RetailAnalystBench smoke suite."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assert-smoke", action="store_true")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--rolling",
        action="store_true",
        help="Run the 30-case rolling historical-window suite.",
    )
    args = parser.parse_args()

    configured = args.data_dir or (
        Path(os.environ["EIW_RETAIL_DATA_DIR"])
        if os.getenv("EIW_RETAIL_DATA_DIR")
        else None
    )
    engine = (
        RetailDataEngine.from_complete_journey(configured)
        if configured is not None
        else RetailDataEngine.demo()
    )
    runner = RetailBenchmarkRunner(RetailBARuntime(engine))
    cases = runner.build_rolling_cases() if args.rolling else None
    result = runner.run(cases)
    rendered = json.dumps(result, indent=2, default=str)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    if args.assert_smoke:
        if float(result["report_completeness"]) < 1.0:
            return 2
        if float(result["action_coverage"]) < 1.0:
            return 3
        if float(result["driver_recall_at_k"]) < 0.90:
            return 4
        if float(result["semantic_coverage"]) < 0.95:
            return 5
        if float(result["numeric_accuracy"]) < 1.0:
            return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
