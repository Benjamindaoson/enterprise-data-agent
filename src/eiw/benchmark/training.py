"""SFT and GRPO-style training on BusinessAgentBench-Hard-v1."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

from eiw.benchmark.hard_env import (
    HARD_ACTION_SPACE,
    HardBusinessEnvironment,
    HardCase,
    HardState,
)
from eiw.benchmark.policies import HardExpertPolicy
from eiw.benchmark.runner import evaluate_hard_policy, run_hard_episode
from eiw.training.policy import (
    PolicyConfig,
    TinyAgentTransformer,
    collate_texts,
    load_policy,
    save_policy,
)

ACTION_TO_ID = {action: index for index, action in enumerate(HARD_ACTION_SPACE)}


class HardTransformerPolicy:
    def __init__(self, model: TinyAgentTransformer) -> None:
        self.model = model

    def choose_action(self, state: HardState) -> str:
        self.model.eval()
        with torch.no_grad():
            tokens, mask = collate_texts([state.policy_features()], self.model.config)
            logits = self.model(tokens, mask)
            return self.model.config.action_space[int(logits.argmax(dim=-1).item())]


def collect_expert_examples(
    cases: list[HardCase],
    *,
    seed: int = 31,
    keep_fraction: float = 1.0,
) -> list[tuple[str, int]]:
    rng = random.Random(seed)
    examples: list[tuple[str, int]] = []
    policy = HardExpertPolicy()
    for index, case in enumerate(cases):
        env = HardBusinessEnvironment(case, seed=index)
        while not env.state.done:
            state_text = env.state.policy_features()
            action = policy.choose_action(env.state)
            if rng.random() <= keep_fraction:
                examples.append((state_text, ACTION_TO_ID[action]))
            env.step(action)
    if not examples:
        raise ValueError("hard SFT examples are empty")
    return examples


def train_hard_sft(
    train_cases: list[HardCase],
    output_path: Path,
    *,
    epochs: int = 8,
    keep_fraction: float = 0.65,
    learning_rate: float = 2e-3,
    seed: int = 37,
) -> dict[str, float | int]:
    torch.manual_seed(seed)
    random.seed(seed)
    examples = collect_expert_examples(
        train_cases,
        seed=seed,
        keep_fraction=keep_fraction,
    )
    config = PolicyConfig(
        max_tokens=96,
        hidden_size=96,
        heads=4,
        layers=2,
        dropout=0.0,
        action_space=HARD_ACTION_SPACE,
    )
    model = TinyAgentTransformer(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    loss_fn = nn.CrossEntropyLoss()
    losses: list[float] = []

    for _ in range(epochs):
        random.shuffle(examples)
        # Small shuffled mini-batches preserve reproducibility while avoiding one giant update.
        for start in range(0, len(examples), 32):
            batch = examples[start:start + 32]
            texts = [item[0] for item in batch]
            labels = torch.tensor([item[1] for item in batch], dtype=torch.long)
            tokens, mask = collate_texts(texts, model.config)
            logits = model(tokens, mask)
            loss = loss_fn(logits, labels)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))

    save_policy(
        model,
        output_path,
        metadata={
            "stage": "hard-sft",
            "examples": len(examples),
            "epochs": epochs,
            "keep_fraction": keep_fraction,
        },
    )
    return {
        "examples": len(examples),
        "epochs": epochs,
        "keep_fraction": keep_fraction,
        "final_loss": losses[-1],
    }


@dataclass(slots=True)
class _RolloutStep:
    state_text: str
    action_id: int
    old_log_prob: float


@dataclass(slots=True)
class _Rollout:
    steps: list[_RolloutStep]
    reward: float
    success: bool


def _sample_rollout(
    model: TinyAgentTransformer,
    case: HardCase,
    *,
    seed: int,
    temperature: float,
) -> _Rollout:
    torch.manual_seed(seed)
    env = HardBusinessEnvironment(case, seed=seed)
    steps: list[_RolloutStep] = []
    total_reward = 0.0
    while not env.state.done:
        state_text = env.state.policy_features()
        tokens, mask = collate_texts([state_text], model.config)
        with torch.no_grad():
            logits = model(tokens, mask)[0] / temperature
            distribution = torch.distributions.Categorical(logits=logits)
            action_id = int(distribution.sample().item())
            old_log_prob = float(
                distribution.log_prob(torch.tensor(action_id)).detach()
            )
        result = env.step(model.config.action_space[action_id])
        total_reward += result.reward
        steps.append(_RolloutStep(state_text, action_id, old_log_prob))
    return _Rollout(steps=steps, reward=total_reward, success=env.state.success)


def train_hard_grpo(
    sft_checkpoint: Path,
    train_cases: list[HardCase],
    output_path: Path,
    *,
    iterations: int = 10,
    group_size: int = 5,
    learning_rate: float = 5e-4,
    temperature: float = 1.15,
    clip_epsilon: float = 0.2,
    trust_beta: float = 0.015,
    seed: int = 41,
) -> dict[str, float | int]:
    torch.manual_seed(seed)
    random.seed(seed)
    model = load_policy(sft_checkpoint)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    mean_rewards: list[float] = []
    success_rates: list[float] = []

    for iteration in range(iterations):
        selected = [
            train_cases[(iteration * 5 + offset) % len(train_cases)]
            for offset in range(min(5, len(train_cases)))
        ]
        rewards_for_iteration: list[float] = []
        successes_for_iteration: list[float] = []

        for case_index, case in enumerate(selected):
            group = [
                _sample_rollout(
                    model,
                    case,
                    seed=seed + iteration * 1000 + case_index * 100 + group_index,
                    temperature=temperature,
                )
                for group_index in range(group_size)
            ]
            rewards = torch.tensor([rollout.reward for rollout in group], dtype=torch.float32)
            advantages = (rewards - rewards.mean()) / rewards.std(unbiased=False).clamp(min=1e-6)
            losses: list[torch.Tensor] = []
            for rollout, advantage in zip(group, advantages, strict=True):
                for step in rollout.steps:
                    tokens, mask = collate_texts([step.state_text], model.config)
                    logits = model(tokens, mask)[0] / temperature
                    log_probs = torch.log_softmax(logits, dim=-1)
                    new_log_prob = log_probs[step.action_id]
                    old_log_prob = torch.tensor(step.old_log_prob)
                    ratio = torch.exp(new_log_prob - old_log_prob)
                    clipped = torch.clamp(ratio, 1 - clip_epsilon, 1 + clip_epsilon)
                    surrogate = torch.minimum(ratio * advantage, clipped * advantage)
                    trust_penalty = (new_log_prob - old_log_prob).pow(2)
                    losses.append(-surrogate + trust_beta * trust_penalty)
                rewards_for_iteration.append(rollout.reward)
                successes_for_iteration.append(float(rollout.success))

            if losses:
                optimizer.zero_grad()
                torch.stack(losses).mean().backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

        mean_rewards.append(sum(rewards_for_iteration) / max(len(rewards_for_iteration), 1))
        success_rates.append(sum(successes_for_iteration) / max(len(successes_for_iteration), 1))

    save_policy(
        model,
        output_path,
        metadata={
            "stage": "hard-grpo",
            "iterations": iterations,
            "group_size": group_size,
        },
    )
    return {
        "iterations": iterations,
        "group_size": group_size,
        "final_rollout_reward": mean_rewards[-1],
        "best_rollout_reward": max(mean_rewards),
        "final_rollout_success_rate": success_rates[-1],
    }


def evaluate_checkpoint(path: Path, cases: list[HardCase]) -> dict[str, float | int]:
    return evaluate_hard_policy(
        HardTransformerPolicy(load_policy(path)),
        cases,
    ).as_dict()
