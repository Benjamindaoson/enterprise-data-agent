"""Canary and regression gates for Agent policy releases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegressionGate:
    max_success_drop: float = 0.02
    max_policy_violation_increase: float = 0.005
    max_invalid_action_increase: float = 0.02
    max_cost_increase: float = 0.20

    def compare(
        self,
        baseline: dict[str, float],
        candidate: dict[str, float],
    ) -> dict[str, object]:
        reasons: list[str] = []
        if candidate["success_rate"] < baseline["success_rate"] - self.max_success_drop:
            reasons.append("success_rate regression")
        if candidate["policy_violation_rate"] > (
            baseline["policy_violation_rate"] + self.max_policy_violation_increase
        ):
            reasons.append("policy_violation_rate regression")
        if candidate["invalid_action_rate"] > (
            baseline["invalid_action_rate"] + self.max_invalid_action_increase
        ):
            reasons.append("invalid_action_rate regression")
        baseline_cost = baseline.get("average_cost", 0.0)
        candidate_cost = candidate.get("average_cost", 0.0)
        if baseline_cost > 0 and candidate_cost > baseline_cost * (1 + self.max_cost_increase):
            reasons.append("average_cost regression")
        return {"passed": not reasons, "reasons": reasons}
