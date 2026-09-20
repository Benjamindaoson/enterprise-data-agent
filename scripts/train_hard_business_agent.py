"""Train SFT then GRPO on BusinessAgentBench-Hard-v1 and compare policies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.policies import DirectPolicy, HardRandomPolicy, PromptHeuristicPolicy
from eiw.benchmark.runner import evaluate_hard_policy
from eiw.benchmark.training import (
    evaluate_checkpoint,
    train_hard_grpo,
    train_hard_sft,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/hard-benchmark"))
    parser.add_argument("--cases", type=int, default=64)
    parser.add_argument("--sft-epochs", type=int, default=8)
    parser.add_argument("--grpo-iterations", type=int, default=10)
    parser.add_argument("--group-size", type=int, default=5)
    args = parser.parse_args()

    cases = generate_cases(args.cases)
    split = max(8, int(len(cases) * 0.75))
    train_cases = cases[:split]
    held_out = cases[split:]
    args.root.mkdir(parents=True, exist_ok=True)

    sft_path = args.root / "hard-sft.pt"
    grpo_path = args.root / "hard-grpo.pt"
    sft_training = train_hard_sft(
        train_cases,
        sft_path,
        epochs=args.sft_epochs,
    )
    sft_eval = evaluate_checkpoint(sft_path, held_out)
    grpo_training = train_hard_grpo(
        sft_path,
        train_cases,
        grpo_path,
        iterations=args.grpo_iterations,
        group_size=args.group_size,
    )
    grpo_eval = evaluate_checkpoint(grpo_path, held_out)

    result = {
        "benchmark": "BusinessAgentBench-Hard-v1",
        "train_cases": len(train_cases),
        "held_out_cases": len(held_out),
        "direct": evaluate_hard_policy(DirectPolicy(), held_out).as_dict(),
        "random": evaluate_hard_policy(HardRandomPolicy(17), held_out).as_dict(),
        "prompt": evaluate_hard_policy(PromptHeuristicPolicy(), held_out).as_dict(),
        "sft_training": sft_training,
        "sft": sft_eval,
        "grpo_training": grpo_training,
        "sft_grpo": grpo_eval,
    }
    (args.root / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
