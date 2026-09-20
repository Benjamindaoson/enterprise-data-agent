"""Reproducible business-agent evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass

from eiw.business.models import BusinessScenario
from eiw.flywheel.trajectory import AgentPolicy, run_episode


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    episodes: int
    success_rate: float
    average_reward: float
    invalid_action_rate: float
    policy_violation_rate: float
    average_steps: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "episodes": self.episodes,
            "success_rate": self.success_rate,
            "average_reward": self.average_reward,
            "invalid_action_rate": self.invalid_action_rate,
            "policy_violation_rate": self.policy_violation_rate,
            "average_steps": self.average_steps,
        }


def evaluate_policy(
    policy: AgentPolicy,
    *,
    seeds: range = range(10),
    public_signal: float = 1.0,
    public_context: dict[str, float | str] | None = None,
) -> EvaluationSummary:
    trajectories = [
        run_episode(
            policy,
            scenario=scenario,
            seed=seed,
            public_signal=public_signal,
            public_context=public_context,
        )
        for scenario in BusinessScenario
        for seed in seeds
    ]
    episodes = len(trajectories)
    steps = sum(len(item.steps) for item in trajectories)
    return EvaluationSummary(
        episodes=episodes,
        success_rate=sum(item.success for item in trajectories) / episodes,
        average_reward=sum(item.total_reward for item in trajectories) / episodes,
        invalid_action_rate=sum(item.invalid_actions for item in trajectories) / max(steps, 1),
        policy_violation_rate=sum(item.policy_violations > 0 for item in trajectories) / episodes,
        average_steps=steps / episodes,
    )
