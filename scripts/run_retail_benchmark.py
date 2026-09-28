#!/usr/bin/env python3
"""Run the deterministic RetailAnalystBench smoke suite."""

from __future__ import annotations

import argparse
import json

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.runtime import RetailBARuntime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assert-smoke", action="store_true")
    args = parser.parse_args()

    result = RetailBenchmarkRunner(RetailBARuntime(RetailDataEngine.demo())).run()
    print(json.dumps(result, indent=2, default=str))

    if args.assert_smoke:
        if float(result["report_completeness"]) < 1.0:
            return 2
        if float(result["action_coverage"]) < 1.0:
            return 3
        if float(result["driver_recall_at_k"]) < 0.5:
            return 4
        if float(result["semantic_coverage"]) < 0.8:
            return 5
        if float(result["numeric_accuracy"]) < 1.0:
            return 6
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
