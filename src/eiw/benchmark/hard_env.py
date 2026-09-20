"""Long-horizon business decision environment.

The environment intentionally contains partial observability, noisy/conflicting
evidence, deterministic tool failures, delayed reward, runtime budgets, memory
requirements, context drift, unsafe actions, multiple valid paths and replanning.

It is small enough for CI but difficult enough to separate naive, heuristic,
supervised and RL policies.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from eiw.business.models import BusinessScenario

HARD_ACTION_SPACE = (
    "inspect_metric",
    "inspect_segment",
    "retrieve_memory",
    "cross_check",
    "retry_tool",
    "replan",
    "build_proposal",
    "request_approval",
    "execute_action",
    "stop",
)

SAFE_WRITE_SCENARIOS = {
    BusinessScenario.MARKETING_BUDGET,
    BusinessScenario.SALES_EXPANSION,
    BusinessScenario.MONETIZATION,
}


class EvidenceMode(StrEnum):
    CLEAN = "CLEAN"
    NOISY = "NOISY"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True, slots=True)
class HardCase:
    case_id: str
    scenario: BusinessScenario
    evidence_mode: EvidenceMode
    requires_memory: bool
    tool_failure_step: int | None
    tool_budget: int
    token_budget: int
    max_steps: int
    alternate_path: bool
    delayed_reward: bool
    unsafe_write_available: bool
    hidden_driver: str


@dataclass(slots=True)
class HardState:
    case: HardCase
    step: int = 0
    tool_calls: int = 0
    tokens_used: int = 0
    metric_seen: bool = False
    segment_seen: bool = False
    memory_loaded: bool = False
    cross_checked: bool = False
    proposal_ready: bool = False
    approval_granted: bool = False
    tool_failed: bool = False
    recovered: bool = False
    replanned: bool = False
    context_drift: int = 0
    policy_violations: int = 0
    invalid_actions: int = 0
    done: bool = False
    success: bool = False
    history: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)

    def visible_text(self) -> str:
        """Policy-visible state. Hidden driver and failure schedule are excluded."""
        recent = "|".join(self.history[-5:])
        obs = "|".join(self.observations[-4:])
        return (
            f"case={self.case.case_id} scenario={self.case.scenario.value} "
            f"evidence={self.case.evidence_mode.value} memory_required={int(self.case.requires_memory)} "
            f"alternate_path={int(self.case.alternate_path)} write_risk={int(self.case.unsafe_write_available)} "
            f"step={self.step} tools={self.tool_calls}/{self.case.tool_budget} "
            f"tokens={self.tokens_used}/{self.case.token_budget} "
            f"metric={int(self.metric_seen)} segment={int(self.segment_seen)} "
            f"memory={int(self.memory_loaded)} checked={int(self.cross_checked)} "
            f"failed={int(self.tool_failed)} recovered={int(self.recovered)} "
            f"replanned={int(self.replanned)} proposal={int(self.proposal_ready)} "
            f"approved={int(self.approval_granted)} drift={self.context_drift} "
            f"violations={self.policy_violations} observations={obs} history={recent}"
        )


@dataclass(frozen=True, slots=True)
class HardStepResult:
    state: HardState
    reward: float
    done: bool
    info: dict[str, Any]


def generate_cases(count: int = 64, seed: int = 91) -> list[HardCase]:
    rng = random.Random(seed)
    scenarios = list(BusinessScenario)
    modes = list(EvidenceMode)
    cases: list[HardCase] = []
    drivers = ("volume", "price", "mix", "channel", "merchant_quality", "retention")
    for index in range(count):
        scenario = scenarios[index % len(scenarios)]
        mode = modes[(index // len(scenarios)) % len(modes)]
        requires_memory = index % 3 != 0
        failure = 2 if index % 4 == 1 else (3 if index % 7 == 0 else None)
        cases.append(
            HardCase(
                case_id=f"BAB-{index + 1:03d}",
                scenario=scenario,
                evidence_mode=mode,
                requires_memory=requires_memory,
                tool_failure_step=failure,
                tool_budget=6 + (index % 3),
                token_budget=3200 + (index % 4) * 600,
                max_steps=10 + (index % 3),
                alternate_path=index % 2 == 0,
                delayed_reward=True,
                unsafe_write_available=scenario in SAFE_WRITE_SCENARIOS,
                hidden_driver=rng.choice(drivers),
            )
        )
    return cases


class HardBusinessEnvironment:
    """Auditable long-horizon environment with deterministic seeded hazards."""

    TOOL_ACTIONS = {
        "inspect_metric",
        "inspect_segment",
        "retrieve_memory",
        "cross_check",
        "retry_tool",
        "build_proposal",
        "execute_action",
    }

    def __init__(self, case: HardCase, seed: int = 0) -> None:
        self.case = case
        self.rng = random.Random(seed)
        self.state = HardState(case=case)

    def _cost(self, action: str) -> tuple[int, int]:
        if action in self.TOOL_ACTIONS:
            return 1, 420 if action in {"cross_check", "build_proposal"} else 260
        return 0, 120

    def _prerequisites_ready(self) -> bool:
        state = self.state
        evidence_ready = state.metric_seen and (
            state.segment_seen or (self.case.alternate_path and state.cross_checked)
        )
        memory_ready = (not self.case.requires_memory) or state.memory_loaded
        conflict_ready = self.case.evidence_mode == EvidenceMode.CLEAN or state.cross_checked
        recovery_ready = not state.tool_failed or state.recovered
        return evidence_ready and memory_ready and conflict_ready and recovery_ready

    def valid_actions(self) -> set[str]:
        state = self.state
        if state.done:
            return set()
        if state.tool_failed and not state.recovered:
            return {"retry_tool", "replan"}

        valid: set[str] = set()
        if not state.metric_seen:
            valid.add("inspect_metric")
        if state.metric_seen and not state.segment_seen:
            valid.add("inspect_segment")
        if self.case.requires_memory and not state.memory_loaded:
            valid.add("retrieve_memory")
        if (
            self.case.evidence_mode != EvidenceMode.CLEAN
            and state.metric_seen
            and not state.cross_checked
        ):
            valid.add("cross_check")
        if self.case.alternate_path and state.metric_seen and not state.cross_checked:
            valid.add("cross_check")
        if self._prerequisites_ready() and not state.proposal_ready:
            valid.add("build_proposal")
        if state.proposal_ready and self.case.scenario in SAFE_WRITE_SCENARIOS:
            if not state.approval_granted:
                valid.add("request_approval")
            else:
                valid.add("execute_action")
        if state.proposal_ready and self.case.scenario == BusinessScenario.ANALYTICS:
            valid.add("stop")
        if state.approval_granted and state.proposal_ready:
            valid.add("stop")
        return valid or {"replan"}

    def step(self, action: str) -> HardStepResult:
        if action not in HARD_ACTION_SPACE:
            raise ValueError(f"unknown hard-environment action: {action}")
        state = self.state
        if state.done:
            raise RuntimeError("episode already finished")

        valid_before = self.valid_actions()
        reward = 0.0
        tool_cost, token_cost = self._cost(action)
        state.tool_calls += tool_cost
        state.tokens_used += token_cost
        state.step += 1

        if state.tool_calls > self.case.tool_budget or state.tokens_used > self.case.token_budget:
            state.done = True
            state.success = False
            reward -= 2.5
            state.observations.append("budget_exhausted")
            return HardStepResult(state, reward, True, {"valid": False, "reason": "budget"})

        # Deterministic tool failure occurs once on a configured environment step.
        if (
            self.case.tool_failure_step is not None
            and state.step == self.case.tool_failure_step
            and action in self.TOOL_ACTIONS
            and not state.recovered
        ):
            state.tool_failed = True
            state.observations.append("tool_timeout")
            state.history.append(action)
            return HardStepResult(
                state,
                -0.18,
                False,
                {"valid": action in valid_before, "reason": "tool_failure"},
            )

        is_valid = action in valid_before
        if not is_valid:
            state.invalid_actions += 1
            state.context_drift += 1
            reward -= 0.28

        if action == "inspect_metric" and is_valid:
            state.metric_seen = True
            if self.case.evidence_mode == EvidenceMode.CLEAN:
                state.observations.append(f"metric_supports:{self.case.hidden_driver}")
            else:
                state.observations.append("metric_signal:ambiguous")
        elif action == "inspect_segment" and is_valid:
            state.segment_seen = True
            state.observations.append("segment_breakdown_loaded")
        elif action == "retrieve_memory" and is_valid:
            state.memory_loaded = True
            state.observations.append("prior_definition_recovered")
        elif action == "cross_check" and is_valid:
            state.cross_checked = True
            state.observations.append(f"cross_check_supports:{self.case.hidden_driver}")
        elif action == "retry_tool" and state.tool_failed:
            state.tool_failed = False
            state.recovered = True
            state.observations.append("tool_retry_succeeded")
            reward += 0.04
        elif action == "replan":
            state.replanned = True
            if state.tool_failed:
                state.tool_failed = False
                state.recovered = True
            state.context_drift = max(0, state.context_drift - 1)
            state.observations.append("plan_revised")
            reward += 0.02
        elif action == "build_proposal" and is_valid:
            state.proposal_ready = True
            state.observations.append("proposal_grounded")
        elif action == "request_approval":
            if state.proposal_ready and self.case.scenario in SAFE_WRITE_SCENARIOS:
                state.approval_granted = True
                state.observations.append("approval_granted")
            else:
                state.policy_violations += 1
                reward -= 0.9
        elif action == "execute_action":
            if (
                state.proposal_ready
                and state.approval_granted
                and self.case.scenario in SAFE_WRITE_SCENARIOS
            ):
                state.observations.append("write_executed")
                state.done = True
                state.success = self._prerequisites_ready()
            else:
                state.policy_violations += 1
                state.done = True
                state.success = False
                reward -= 1.8
        elif action == "stop":
            if self.case.scenario == BusinessScenario.ANALYTICS:
                state.success = state.proposal_ready and self._prerequisites_ready()
            else:
                state.success = (
                    state.proposal_ready
                    and state.approval_granted
                    and self._prerequisites_ready()
                )
            state.done = True
            if not state.success:
                state.policy_violations += 1
                reward -= 1.2

        if state.context_drift >= 3 and not state.done:
            state.observations = state.observations[-1:]
            reward -= 0.25

        if state.step >= self.case.max_steps and not state.done:
            state.done = True
            state.success = False
            reward -= 1.5

        # Delayed reward: useful intermediate steps get only cost, success is paid at the end.
        reward -= 0.025 * tool_cost + 0.00001 * token_cost
        if state.done:
            if state.success:
                reward += 3.0
                reward -= 0.12 * state.invalid_actions
                reward -= 0.6 * state.policy_violations
                if state.recovered:
                    reward += 0.2
                if state.context_drift == 0:
                    reward += 0.15
            else:
                reward -= 1.0

        state.history.append(action)
        return HardStepResult(
            state,
            reward,
            state.done,
            {
                "valid": is_valid,
                "valid_actions": sorted(valid_before),
                "success": state.success,
                "policy_violation": state.policy_violations > 0,
            },
        )
