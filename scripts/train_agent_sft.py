"""Train and evaluate the supervised Agent skill-selection policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.flywheel.evaluation import evaluate_policy
from eiw.training.policy import TransformerPolicy, load_policy
from eiw.training.sft import train_sft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("artifacts/flywheel/sft-dataset.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/models/agent-sft.pt"))
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    metrics = train_sft(args.dataset, args.output, epochs=args.epochs)
    evaluation = evaluate_policy(TransformerPolicy(load_policy(args.output)), seeds=range(10)).as_dict()
    print(json.dumps({"training": metrics, "evaluation": evaluation}, indent=2))


if __name__ == "__main__":
    main()
