"""Deterministic business-operations simulator for Agent policy training.

The environment uses the real public Iowa wholesale snapshot when available to
parameterize business signals, while campaign/CRM/monetization outcomes are
simulated. This keeps the public repository reproducible without claiming
access to proprietary operational systems.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from eiw.business.models import BusinessScenario
from eiw.workspace.data import IowaData

ACTION_SPACE = (
    "business.metric_analysis",
    "business.attribution",
    "business.marketing_budget",
    "business.sales_expansion",
    "business.monetization",
    "runtime.verify_action",
    "runtime.stop",
)

EXPECTED_PATHS: dict[BusinessScenario, tuple[str, ...]] = {
    BusinessScenario.ANALYTICS: (
        "business.metric_analysis",
        "business.attribution",
        "runtime.verify_action",
        "runtime.stop",
    ),
    BusinessScenario.MARKETING_BUDGET: (
        "business.metric_analysis",
        "business.marketing_budget",
        "runtime.verify_action",
        "runtime.stop",
    ),
    BusinessScenario.SALES_EXPANSION: (
        "business.metric_analysis",
        "business.sales_expansion",
        "runtime.verify_action",
        "runtime.stop",
    ),
    BusinessScenario.MONETIZATION: (
        "business.metric_analysis",
        "business.monetization",
        "runtime.verify_action",
        "runtime.stop",
    ),
}


@dataclass(slots=True)
class SimulatorState:
    scenario: BusinessScenario
    goal: str
    step_index: int = 0
    evidence_ready: bool = False
    proposal_ready: bool = False
    verified: bool = False
    done: bool = False
    success: bool = False
    invalid_actions: int = 0
    policy_violations: int = 0
    cumulative_cost: float = 0.0
    public_signal: float = 1.0
    public_context: dict[str, float | str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    def as_policy_text(self) -> str:
        return (
            f"scenario={self.scenario.value} goal={self.goal} step={self.step_index} "
            f"evidence={int(self.evidence_ready)} proposal={int(self.proposal_ready)} "
            f"verified={int(self.verified)} invalid={self.invalid_actions} "
            f"violations={self.policy_violations} cost={self.cumulative_cost:.3f} "
            f"signal={self.public_signal:.3f} "
            f"snapshot={self.public_context.get('snapshot_id', 'fixture')} "
            f"latest_sales={self.public_context.get('latest_sales', 0)} "
            f"latest_bottles={self.public_context.get('latest_bottles', 0)} "
            f"history={'|'.join(self.history[-4:])}"
        )


@dataclass(slots=True)
class StepResult:
    state: SimulatorState
    reward: float
    done: bool
    info: dict[str, Any]


class BusinessOperationsSimulator:
    """Small, auditable MDP for long-horizon skill-selection experiments."""

    def __init__(
        self,
        seed: int = 0,
        public_signal: float = 1.0,
        public_context: dict[str, float | str] | None = None,
    ) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.public_signal = public_signal
        self.public_context = public_context or {"snapshot_id": "deterministic-fixture"}
        self.state: SimulatorState | None = None

    @classmethod
    def from_public_data(cls, data: IowaData, seed: int = 0) -> "BusinessOperationsSimulator":
        if not data.available():
            return cls(seed=seed)

        status = data.status()
        through = date.fromisoformat(str(status["measured_business_date_max"]))
        start = through.replace(day=1)
        rows = data.aggregate(
            start,
            through,
            ["wholesale_sales_amount", "bottles_ordered", "average_wholesale_price_per_bottle"],
        )
        latest = rows[0] if rows else {}
        sales = float(latest.get("wholesale_sales_amount") or 0.0)
        bottles = float(latest.get("bottles_ordered") or 0.0)
        price = float(latest.get("average_wholesale_price_per_bottle") or 0.0)
        signal = max(0.75, min(1.25, 0.75 + price / 40.0))
        context: dict[str, float | str] = {
            "snapshot_id": data.snapshot_id,
            "measured_row_count": float(status.get("measured_row_count", 0) or 0),
            "latest_sales": round(sales, 2),
            "latest_bottles": round(bottles, 2),
            "latest_avg_price": round(price, 4),
        }
        return cls(seed=seed, public_signal=signal, public_context=context)

    def reset(self, scenario: BusinessScenario) -> SimulatorState:
        goals = {
            BusinessScenario.ANALYTICS: "explain a business change with evidence",
            BusinessScenario.MARKETING_BUDGET: "allocate budget without unauthorized spend",
            BusinessScenario.SALES_EXPANSION: "prioritize merchant leads for constrained sales capacity",
            BusinessScenario.MONETIZATION: "identify monetization opportunities with verified evidence",
        }
        self.state = SimulatorState(
            scenario=scenario,
            goal=goals[scenario],
            public_signal=self.public_signal,
            public_context=dict(self.public_context),
        )
        return self.state

    def valid_actions(self) -> set[str]:
        if self.state is None or self.state.done:
            return set()
        expected = EXPECTED_PATHS[self.state.scenario]
        valid = {expected[min(self.state.step_index, len(expected) - 1)]}
        if self.state.evidence_ready:
            valid.add("runtime.verify_action")
        if self.state.verified:
            valid.add("runtime.stop")
        return valid

    def step(self, action: str) -> StepResult:
        if self.state is None:
            raise RuntimeError("reset() must be called before step()")
        if self.state.done:
            raise RuntimeError("episode already finished")
        if action not in ACTION_SPACE:
            raise ValueError(f"unknown action: {action}")

        state = self.state
        expected_path = EXPECTED_PATHS[state.scenario]
        expected = expected_path[min(state.step_index, len(expected_path) - 1)]
        reward = -0.04  # per-step inference/tool cost
        info: dict[str, Any] = {"expected_action": expected, "valid": action in self.valid_actions()}

        if action == expected:
            reward += 1.0
            state.step_index += 1
            if action == "business.metric_analysis":
                state.evidence_ready = True
            elif action in {
                "business.attribution",
                "business.marketing_budget",
                "business.sales_expansion",
                "business.monetization",
            }:
                state.proposal_ready = True
            elif action == "runtime.verify_action":
                if state.evidence_ready and state.proposal_ready:
                    state.verified = True
                else:
                    reward -= 0.75
                    state.invalid_actions += 1
            elif action == "runtime.stop":
                state.done = True
                state.success = state.verified
                reward += 2.0 if state.success else -1.5
        else:
            state.invalid_actions += 1
            reward -= 0.6
            if action == "runtime.stop" and not state.verified:
                state.policy_violations += 1
                reward -= 1.4
                state.done = True
            elif (
                state.scenario == BusinessScenario.MARKETING_BUDGET
                and action == "business.marketing_budget"
                and not state.evidence_ready
            ):
                state.policy_violations += 1
                reward -= 1.0

        state.cumulative_cost += 0.04
        state.history.append(action)
        if len(state.history) >= 8 and not state.done:
            state.done = True
            reward -= 1.0
        info["success"] = state.success
        info["policy_violation"] = state.policy_violations > 0
        return StepResult(state=state, reward=reward * state.public_signal, done=state.done, info=info)
