"""Fail CI when a candidate Agent policy violates release thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.production.canary import RegressionGate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    result = RegressionGate().compare(baseline, candidate)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
