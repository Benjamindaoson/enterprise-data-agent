"""Run GRPO-style AgentRL from the supervised policy checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.flywheel.evaluation import evaluate_policy
from eiw.training.grpo import train_grpo
from eiw.training.policy import TransformerPolicy, load_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sft", type=Path, default=Path("artifacts/models/agent-sft.pt"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/models/agent-grpo.pt"))
    parser.add_argument("--iterations", type=int, default=12)
    parser.add_argument("--group-size", type=int, default=6)
    args = parser.parse_args()

    before = evaluate_policy(TransformerPolicy(load_policy(args.sft)), seeds=range(10)).as_dict()
    training = train_grpo(
        args.sft,
        args.output,
        iterations=args.iterations,
        group_size=args.group_size,
    )
    after = evaluate_policy(TransformerPolicy(load_policy(args.output)), seeds=range(10)).as_dict()
    print(json.dumps({"before": before, "training": training, "after": after}, indent=2))


if __name__ == "__main__":
    main()
