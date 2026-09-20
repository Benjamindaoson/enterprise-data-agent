"""Trajectory contracts and durable JSONL storage."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from eiw.business.models import BusinessScenario
from eiw.business.simulator import BusinessOperationsSimulator, SimulatorState


class AgentPolicy(Protocol):
    def choose_action(self, state: SimulatorState) -> str: ...


@dataclass(slots=True)
class TrajectoryStep:
    state_text: str
    action: str
    reward: float
    expected_action: str
    valid: bool
    policy_violation: bool


@dataclass(slots=True)
class Trajectory:
    trajectory_id: str
    scenario: str
    seed: int
    steps: list[TrajectoryStep] = field(default_factory=list)
    total_reward: float = 0.0
    success: bool = False
    invalid_actions: int = 0
    policy_violations: int = 0


class TrajectoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, trajectory: Trajectory) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(trajectory), sort_keys=True) + "\n")

    def load(self) -> list[Trajectory]:
        if not self.path.exists():
            return []
        output: list[Trajectory] = []
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            item["steps"] = [TrajectoryStep(**step) for step in item.get("steps", [])]
            output.append(Trajectory(**item))
        return output

    def export_sft(self, path: Path, *, successful_only: bool = True) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with path.open("w", encoding="utf-8") as handle:
            for trajectory in self.load():
                if successful_only and not trajectory.success:
                    continue
                for step in trajectory.steps:
                    if step.valid:
                        handle.write(json.dumps({"input": step.state_text, "target": step.action}) + "\n")
                        count += 1
        return count

    def failure_report(self) -> dict[str, object]:
        trajectories = self.load()
        failures = [item for item in trajectories if not item.success]
        action_counts: dict[str, int] = {}
        for trajectory in failures:
            for step in trajectory.steps:
                if not step.valid:
                    action_counts[step.action] = action_counts.get(step.action, 0) + 1
        return {
            "trajectory_count": len(trajectories),
            "failure_count": len(failures),
            "failure_rate": len(failures) / len(trajectories) if trajectories else 0.0,
            "invalid_action_counts": dict(sorted(action_counts.items())),
        }


def run_episode(
    policy: AgentPolicy,
    *,
    scenario: BusinessScenario,
    seed: int,
    public_signal: float = 1.0,
) -> Trajectory:
    simulator = BusinessOperationsSimulator(seed=seed, public_signal=public_signal)
    state = simulator.reset(scenario)
    trajectory = Trajectory(
        trajectory_id=str(uuid4()),
        scenario=scenario.value,
        seed=seed,
    )
    while not state.done:
        state_text = state.as_policy_text()
        action = policy.choose_action(state)
        result = simulator.step(action)
        trajectory.steps.append(
            TrajectoryStep(
                state_text=state_text,
                action=action,
                reward=result.reward,
                expected_action=str(result.info["expected_action"]),
                valid=bool(result.info["valid"]),
                policy_violation=bool(result.info["policy_violation"]),
            )
        )
        trajectory.total_reward += result.reward
        state = result.state
    trajectory.success = state.success
    trajectory.invalid_actions = state.invalid_actions
    trajectory.policy_violations = state.policy_violations
    return trajectory
