"""Export expert BusinessAgentBench trajectories for real-LLM SFT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.llm_agent.dataset import export_llm_sft_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("artifacts/llm/sft-train.jsonl"))
    parser.add_argument("--cases", type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(export_llm_sft_dataset(args.output, cases=args.cases), indent=2))


if __name__ == "__main__":
    main()
