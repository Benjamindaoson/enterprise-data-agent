"""Run deterministic reference policies on BusinessAgentBench."""

from __future__ import annotations

import argparse
import json

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.policies import (
    DirectPolicy,
    HardExpertPolicy,
    HardRandomPolicy,
    PromptHeuristicPolicy,
)
from eiw.benchmark.runner import evaluate_hard_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=64)
    args = parser.parse_args()
    cases = generate_cases(args.cases)
    result = {
        "benchmark": "BusinessAgentBench-Hard-v1",
        "cases": len(cases),
        "direct": evaluate_hard_policy(DirectPolicy(), cases).as_dict(),
        "random": evaluate_hard_policy(HardRandomPolicy(17), cases).as_dict(),
        "prompt": evaluate_hard_policy(PromptHeuristicPolicy(), cases).as_dict(),
        "expert": evaluate_hard_policy(HardExpertPolicy(), cases).as_dict(),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
