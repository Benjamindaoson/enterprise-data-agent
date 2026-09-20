"""Evaluate base/prompt/SFT/GRPO open-weight LLM policies on held-out hard cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.runner import evaluate_hard_policy
from eiw.llm_agent.backend import LocalCausalLMActionPolicy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--base-prompt", action="store_true")
    parser.add_argument("--cases", type=int, default=16)
    args = parser.parse_args()
    all_cases = generate_cases(max(64, args.cases * 4))
    held_out = all_cases[-args.cases:]
    policy = LocalCausalLMActionPolicy(
        args.model,
        adapter_path=args.adapter,
        prompted=not args.base_prompt,
    )
    summary = evaluate_hard_policy(policy, held_out)
    print(json.dumps({
        "model": args.model,
        "adapter": str(args.adapter) if args.adapter else None,
        "prompted": not args.base_prompt,
        "held_out_cases": len(held_out),
        "metrics": summary.as_dict(),
    }, indent=2))


if __name__ == "__main__":
    main()
