#!/usr/bin/env python3
"""Export Retail benchmark cases for Agent Lightning rollout datasets."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.domain import build_retail_domain_runtime


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/agent-lightning/retail-cases.jsonl"),
    )
    parser.add_argument("--rolling-windows", type=int, default=5)
    args = parser.parse_args()

    domain = build_retail_domain_runtime()
    runner = RetailBenchmarkRunner(domain.agent)
    cases = [*runner.build_cases()]
    if args.rolling_windows > 0:
        cases.extend(runner.build_rolling_cases(windows=args.rolling_windows))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for case in cases:
            payload = asdict(case)
            payload["expected_driver_terms"] = list(case.expected_driver_terms)
            payload["expected_metrics"] = list(case.expected_metrics)
            payload["expected_dimensions"] = list(case.expected_dimensions)
            payload["expected_intents"] = list(case.expected_intents)
            payload["current_weeks"] = list(case.current_weeks)
            payload["previous_weeks"] = list(case.previous_weeks)
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(json.dumps({"output": str(args.output), "cases": len(cases)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
