"""LoRA SFT for a real open-weight LLM agent policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.llm_agent.sft_lora import train_lora_sft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("artifacts/llm/sft-train.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/models/qwen3-agent-sft"))
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(train_lora_sft(
        args.dataset,
        args.output,
        model_name=args.model,
        epochs=args.epochs,
    ), indent=2))


if __name__ == "__main__":
    main()
