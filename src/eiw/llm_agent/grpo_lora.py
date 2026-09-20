"""Action-level grouped relative policy optimization for a LoRA causal LM.

This optimizes the probability of discrete tool/skill actions under long-horizon
environment rewards. It is intentionally narrower and more auditable than
free-form language RL.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eiw.benchmark.hard_env import (
    HARD_ACTION_SPACE,
    HardBusinessEnvironment,
    HardCase,
    generate_cases,
)
from eiw.llm_agent.prompts import build_action_prompt


@dataclass(slots=True)
class LLMRolloutStep:
    state_text: str
    action: str
    old_log_prob: float


@dataclass(slots=True)
class LLMRollout:
    steps: list[LLMRolloutStep]
    reward: float
    success: bool


def train_lora_grpo(
    sft_adapter: Path,
    output_dir: Path,
    *,
    model_name: str = "Qwen/Qwen3-0.6B",
    iterations: int = 1,
    group_size: int = 2,
    cases_per_iteration: int = 4,
    learning_rate: float = 5e-6,
    clip_epsilon: float = 0.2,
    trust_beta: float = 0.02,
    temperature: float = 1.0,
    seed: int = 23,
) -> dict[str, Any]:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("install the llm extra: pip install -e '.[llm]'") from exc

    torch.manual_seed(seed)
    random.seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    base = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
    )
    model = PeftModel.from_pretrained(base, str(sft_adapter), is_trainable=True)
    device = next(model.parameters()).device
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=learning_rate,
    )

    def action_log_probs(state_text: str) -> Any:
        prompt = build_action_prompt(state_text, prompted=True)
        prompt_ids = tokenizer(prompt, add_special_tokens=True)["input_ids"]
        totals = []
        for action in HARD_ACTION_SPACE:
            action_ids = tokenizer(" " + action, add_special_tokens=False)["input_ids"]
            ids = prompt_ids + action_ids
            input_ids = torch.tensor([ids], dtype=torch.long, device=device)
            logits = model(input_ids=input_ids).logits[0]
            log_probs = torch.log_softmax(logits, dim=-1)
            start = len(prompt_ids) - 1
            total = torch.stack(
                [log_probs[start + offset, token_id] for offset, token_id in enumerate(action_ids)]
            ).sum()
            totals.append(total)
        return torch.stack(totals)

    # Collect rewards directly from the environment so optimization remains auditable.
    def collect_with_reward(case: HardCase, rollout_seed: int) -> LLMRollout:
        env = HardBusinessEnvironment(case, seed=rollout_seed)
        steps: list[LLMRolloutStep] = []
        total_reward = 0.0
        while not env.state.done:
            state_text = env.state.visible_text()
            with torch.no_grad():
                scores = action_log_probs(state_text)
                dist = torch.distributions.Categorical(logits=scores / temperature)
                action_id = int(dist.sample().item())
                old_log_prob = float(dist.log_prob(torch.tensor(action_id, device=device)).cpu())
            action = HARD_ACTION_SPACE[action_id]
            result = env.step(action)
            total_reward += result.reward
            steps.append(LLMRolloutStep(state_text, action, old_log_prob))
        return LLMRollout(steps=steps, reward=total_reward, success=env.state.success)

    cases = generate_cases(max(16, cases_per_iteration * 2), seed=seed)
    reward_history: list[float] = []
    success_history: list[float] = []

    for iteration in range(iterations):
        iteration_rewards: list[float] = []
        iteration_successes: list[float] = []
        selected = cases[iteration * cases_per_iteration:(iteration + 1) * cases_per_iteration]
        if len(selected) < cases_per_iteration:
            selected = cases[:cases_per_iteration]

        for case_index, case in enumerate(selected):
            group = [
                collect_with_reward(case, seed + iteration * 1000 + case_index * 100 + group_index)
                for group_index in range(group_size)
            ]
            rewards = torch.tensor([item.reward for item in group], dtype=torch.float32, device=device)
            advantages = (rewards - rewards.mean()) / rewards.std(unbiased=False).clamp(min=1e-6)
            losses = []
            for rollout, advantage in zip(group, advantages, strict=True):
                for step in rollout.steps:
                    scores = action_log_probs(step.state_text)
                    log_probs = torch.log_softmax(scores / temperature, dim=-1)
                    action_id = HARD_ACTION_SPACE.index(step.action)
                    new_log_prob = log_probs[action_id]
                    old_log_prob = torch.tensor(step.old_log_prob, device=device)
                    ratio = torch.exp(new_log_prob - old_log_prob)
                    clipped = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon)
                    surrogate = torch.minimum(ratio * advantage, clipped * advantage)
                    trust_penalty = (new_log_prob - old_log_prob).pow(2)
                    losses.append(-surrogate + trust_beta * trust_penalty)
                iteration_rewards.append(rollout.reward)
                iteration_successes.append(float(rollout.success))

            if losses:
                optimizer.zero_grad()
                torch.stack(losses).mean().backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

        reward_history.append(sum(iteration_rewards) / max(len(iteration_rewards), 1))
        success_history.append(sum(iteration_successes) / max(len(iteration_successes), 1))

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    metrics = {
        "model_name": model_name,
        "iterations": iterations,
        "group_size": group_size,
        "cases_per_iteration": cases_per_iteration,
        "final_mean_reward": reward_history[-1],
        "final_success_rate": success_history[-1],
        "best_mean_reward": max(reward_history),
    }
    (output_dir / "training-metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics
