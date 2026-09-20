"""Enforce measured BusinessAgentBench-Hard-v1 acceptance criteria."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def evaluate_acceptance(result: dict[str, object]) -> dict[str, object]:
    direct = result["direct"]
    random = result["random"]
    prompt = result["prompt"]
    sft = result["sft"]
    grpo = result["sft_grpo"]
    assert isinstance(direct, dict)
    assert isinstance(random, dict)
    assert isinstance(prompt, dict)
    assert isinstance(sft, dict)
    assert isinstance(grpo, dict)

    checks = {
        "direct_random_are_weak": (
            float(direct["success_rate"]) <= 0.10
            and float(random["success_rate"]) <= 0.10
        ),
        "prompt_beats_direct": float(prompt["success_rate"]) > float(direct["success_rate"]),
        "sft_beats_prompt_success": float(sft["success_rate"]) > float(prompt["success_rate"]),
        "grpo_does_not_regress_success": (
            float(grpo["success_rate"]) >= float(sft["success_rate"])
        ),
        "grpo_improves_reward": float(grpo["average_reward"]) > float(sft["average_reward"]),
        "grpo_reduces_invalid_actions": (
            float(grpo["invalid_action_rate"]) < float(sft["invalid_action_rate"])
        ),
        "grpo_does_not_worsen_policy_violations": (
            float(grpo["policy_violation_rate"]) <= float(sft["policy_violation_rate"])
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "summary": {
            "direct_success": direct["success_rate"],
            "random_success": random["success_rate"],
            "prompt_success": prompt["success_rate"],
            "sft_success": sft["success_rate"],
            "sft_reward": sft["average_reward"],
            "grpo_success": grpo["success_rate"],
            "grpo_reward": grpo["average_reward"],
            "sft_invalid_action_rate": sft["invalid_action_rate"],
            "grpo_invalid_action_rate": grpo["invalid_action_rate"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("artifacts/hard-benchmark/results.json"),
    )
    args = parser.parse_args()
    result = json.loads(args.results.read_text())
    acceptance = evaluate_acceptance(result)
    print(json.dumps(acceptance, indent=2))
    if not acceptance["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
