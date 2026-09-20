"""Trajectory collection and evaluation for BusinessAgentBench."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from eiw.benchmark.hard_env import HardBusinessEnvironment, HardCase, HardState


class HardPolicy(Protocol):
    def choose_action(self, state: HardState) -> str: ...


@dataclass(slots=True)
class HardTrajectoryStep:
    state_text: str
    action: str
    reward: float
    valid: bool
    policy_violation: bool


@dataclass(slots=True)
class HardTrajectory:
    case_id: str
    steps: list[HardTrajectoryStep] = field(default_factory=list)
    total_reward: float = 0.0
    success: bool = False
    invalid_actions: int = 0
    policy_violations: int = 0
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class HardEvaluation:
    cases: int
    success_rate: float
    average_reward: float
    invalid_action_rate: float
    policy_violation_rate: float
    recovery_rate: float
    average_steps: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "cases": self.cases,
            "success_rate": self.success_rate,
            "average_reward": self.average_reward,
            "invalid_action_rate": self.invalid_action_rate,
            "policy_violation_rate": self.policy_violation_rate,
            "recovery_rate": self.recovery_rate,
            "average_steps": self.average_steps,
        }


def run_hard_episode(policy: HardPolicy, case: HardCase, *, seed: int = 0) -> HardTrajectory:
    env = HardBusinessEnvironment(case, seed=seed)
    trajectory = HardTrajectory(case_id=case.case_id)
    while not env.state.done:
        state_text = env.state.visible_text()
        action = policy.choose_action(env.state)
        result = env.step(action)
        trajectory.steps.append(
            HardTrajectoryStep(
                state_text=state_text,
                action=action,
                reward=result.reward,
                valid=bool(result.info.get("valid", False)),
                policy_violation=bool(result.info.get("policy_violation", False)),
            )
        )
        trajectory.total_reward += result.reward
    trajectory.success = env.state.success
    trajectory.invalid_actions = env.state.invalid_actions
    trajectory.policy_violations = env.state.policy_violations
    trajectory.recovered = env.state.recovered
    return trajectory


def evaluate_hard_policy(policy: HardPolicy, cases: list[HardCase]) -> HardEvaluation:
    trajectories = [
        run_hard_episode(policy, case, seed=index)
        for index, case in enumerate(cases)
    ]
    steps = sum(len(item.steps) for item in trajectories)
    failure_cases = sum(case.tool_failure_step is not None for case in cases)
    recovered_failures = sum(
        item.recovered
        for item, case in zip(trajectories, cases, strict=True)
        if case.tool_failure_step is not None
    )
    return HardEvaluation(
        cases=len(cases),
        success_rate=sum(item.success for item in trajectories) / max(len(cases), 1),
        average_reward=sum(item.total_reward for item in trajectories) / max(len(cases), 1),
        invalid_action_rate=sum(item.invalid_actions for item in trajectories) / max(steps, 1),
        policy_violation_rate=sum(item.policy_violations > 0 for item in trajectories)
        / max(len(cases), 1),
        recovery_rate=recovered_failures / max(failure_cases, 1),
        average_steps=steps / max(len(cases), 1),
    )
