"""Cost, permission and human-approval guardrails for agent actions."""

from __future__ import annotations

from dataclasses import dataclass, field

from eiw.business.models import ActionRisk, ProposedAction


@dataclass(slots=True)
class RuntimeBudget:
    max_tool_calls: int = 20
    max_tokens: int = 24_000
    used_tool_calls: int = 0
    used_tokens: int = 0

    def reserve(self, *, tool_calls: int = 0, tokens: int = 0) -> None:
        if self.used_tool_calls + tool_calls > self.max_tool_calls:
            raise RuntimeError("tool-call budget exceeded")
        if self.used_tokens + tokens > self.max_tokens:
            raise RuntimeError("token budget exceeded")
        self.used_tool_calls += tool_calls
        self.used_tokens += tokens

    @property
    def remaining_tool_calls(self) -> int:
        return self.max_tool_calls - self.used_tool_calls

    @property
    def remaining_tokens(self) -> int:
        return self.max_tokens - self.used_tokens


@dataclass(slots=True)
class ActionPolicy:
    permissions: set[str] = field(default_factory=set)
    allow_financial_execution: bool = False

    def evaluate(
        self,
        action: ProposedAction,
        *,
        required_permissions: set[str] | None = None,
        approved: bool = False,
    ) -> dict[str, object]:
        required = required_permissions or set()
        missing = sorted(required - self.permissions)
        reasons: list[str] = []
        allowed = not missing

        if missing:
            reasons.append("missing permissions: " + ", ".join(missing))
        if action.risk == ActionRisk.FINANCIAL_COMMITMENT:
            if not self.allow_financial_execution:
                allowed = False
                reasons.append("financial execution disabled by policy")
            if action.requires_approval and not approved:
                allowed = False
                reasons.append("human approval required")
        if not reasons:
            reasons.append("policy checks passed")
        return {
            "allowed": allowed,
            "reasons": reasons,
            "risk": action.risk.value,
            "requires_approval": action.requires_approval,
        }
