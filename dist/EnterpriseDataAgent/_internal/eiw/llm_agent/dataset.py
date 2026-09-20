"""Create supervised tool/action trajectories for open-weight LLM post-training."""

from __future__ import annotations

import json
from pathlib import Path

from eiw.benchmark.hard_env import generate_cases
from eiw.benchmark.policies import HardExpertPolicy
from eiw.benchmark.runner import run_hard_episode
from eiw.llm_agent.prompts import build_action_prompt


def export_llm_sft_dataset(
    path: Path,
    *,
    cases: int = 64,
    train_fraction: float = 0.75,
) -> dict[str, int]:
    all_cases = generate_cases(cases)
    split = max(1, int(len(all_cases) * train_fraction))
    train_cases = all_cases[:split]
    eval_cases = all_cases[split:]
    path.parent.mkdir(parents=True, exist_ok=True)
    eval_path = path.with_name(path.stem + "-eval.jsonl")
    policy = HardExpertPolicy()

    def write(target: Path, selected: list) -> int:
        count = 0
        with target.open("w", encoding="utf-8") as handle:
            for index, case in enumerate(selected):
                trajectory = run_hard_episode(policy, case, seed=index)
                for step in trajectory.steps:
                    handle.write(
                        json.dumps(
                            {
                                "case_id": case.case_id,
                                "prompt": build_action_prompt(step.state_text, prompted=True),
                                "target": step.action,
                            }
                        )
                        + "\n"
                    )
                    count += 1
        return count

    return {
        "train_examples": write(path, train_cases),
        "eval_examples": write(eval_path, eval_cases),
        "train_cases": len(train_cases),
        "eval_cases": len(eval_cases),
    }
