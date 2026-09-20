"""Group-relative policy optimization over long-horizon business-agent rollouts."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from pathlib import Path

import torch

from eiw.business.models import BusinessScenario
from eiw.business.simulator import BusinessOperationsSimulator
from eiw.training.policy import (
    ID_TO_ACTION,
    TinyAgentTransformer,
    collate_texts,
    load_policy,
    save_policy,
)


@dataclass(slots=True)
class RolloutStep:
    state_text: str
    action_id: int
    old_log_prob: float


@dataclass(slots=True)
class Rollout:
    steps: list[RolloutStep]
    reward: float
    success: bool


def _rollout(model: TinyAgentTransformer, scenario: BusinessScenario, seed: int, temperature: float) -> Rollout:
    simulator = BusinessOperationsSimulator(seed=seed)
    state = simulator.reset(scenario)
    steps: list[RolloutStep] = []
    reward = 0.0
    while not state.done:
        state_text = state.as_policy_text()
        tokens, mask = collate_texts([state_text], model.config)
        with torch.no_grad():
            logits = model(tokens, mask)[0] / temperature
            dist = torch.distributions.Categorical(logits=logits)
            action_id = int(dist.sample().item())
            old_log_prob = float(dist.log_prob(torch.tensor(action_id)).item())
        result = simulator.step(ID_TO_ACTION[action_id])
        reward += result.reward
        steps.append(RolloutStep(state_text, action_id, old_log_prob))
        state = result.state
    return Rollout(steps=steps, reward=reward, success=state.success)


def train_grpo(
    sft_checkpoint: Path,
    output_path: Path,
    *,
    iterations: int = 12,
    group_size: int = 6,
    learning_rate: float = 8e-4,
    clip_epsilon: float = 0.2,
    kl_beta: float = 0.02,
    temperature: float = 1.1,
    seed: int = 13,
) -> dict[str, float | int]:
    torch.manual_seed(seed)
    random.seed(seed)
    model = load_policy(sft_checkpoint)
    reference = copy.deepcopy(model).eval()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    reward_history: list[float] = []
    success_history: list[float] = []

    for iteration in range(iterations):
        iteration_rewards: list[float] = []
        iteration_successes: list[float] = []
        for scenario in BusinessScenario:
            group = [
                _rollout(model, scenario, seed + iteration * 100 + index, temperature)
                for index in range(group_size)
            ]
            rewards = torch.tensor([item.reward for item in group], dtype=torch.float32)
            mean = rewards.mean()
            std = rewards.std(unbiased=False).clamp(min=1e-6)
            advantages = (rewards - mean) / std
            losses: list[torch.Tensor] = []

            for rollout, advantage in zip(group, advantages, strict=True):
                for step in rollout.steps:
                    tokens, mask = collate_texts([step.state_text], model.config)
                    logits = model(tokens, mask)[0]
                    log_probs = torch.log_softmax(logits, dim=-1)
                    new_log_prob = log_probs[step.action_id]
                    ratio = torch.exp(new_log_prob - step.old_log_prob)
                    clipped = torch.clamp(ratio, 1.0 - clip_epsilon, 1.0 + clip_epsilon)
                    surrogate = torch.minimum(ratio * advantage, clipped * advantage)

                    with torch.no_grad():
                        ref_logits = reference(tokens, mask)[0]
                        ref_log_probs = torch.log_softmax(ref_logits, dim=-1)
                    probs = torch.softmax(logits, dim=-1)
                    kl = torch.sum(probs * (log_probs - ref_log_probs))
                    losses.append(-surrogate + kl_beta * kl)

                iteration_rewards.append(rollout.reward)
                iteration_successes.append(float(rollout.success))

            if losses:
                loss = torch.stack(losses).mean()
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

        reward_history.append(sum(iteration_rewards) / max(len(iteration_rewards), 1))
        success_history.append(sum(iteration_successes) / max(len(iteration_successes), 1))

    metrics: dict[str, float | int] = {
        "iterations": iterations,
        "group_size": group_size,
        "final_mean_rollout_reward": reward_history[-1],
        "final_rollout_success_rate": success_history[-1],
        "best_mean_rollout_reward": max(reward_history),
    }
    save_policy(model, output_path, metadata={"stage": "grpo", **metrics})
    return metrics
