"""GRPO-style action policy optimization for the LoRA LLM agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.llm_agent.grpo_lora import train_lora_grpo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sft", type=Path, default=Path("artifacts/models/qwen3-agent-sft"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/models/qwen3-agent-grpo"))
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--group-size", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(train_lora_grpo(
        args.sft,
        args.output,
        model_name=args.model,
        iterations=args.iterations,
        group_size=args.group_size,
    ), indent=2))


if __name__ == "__main__":
    main()
