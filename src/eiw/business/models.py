"""Contracts for business-intelligence and autonomous-operation tasks."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BusinessModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class BusinessScenario(StrEnum):
    ANALYTICS = "ANALYTICS"
    MARKETING_BUDGET = "MARKETING_BUDGET"
    SALES_EXPANSION = "SALES_EXPANSION"
    MONETIZATION = "MONETIZATION"


class ActionRisk(StrEnum):
    READ_ONLY = "READ_ONLY"
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"
    FINANCIAL_COMMITMENT = "FINANCIAL_COMMITMENT"


class BusinessConstraint(BusinessModel):
    name: str = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=20)
    value: Any
    unit: str | None = None


class BusinessObjective(BusinessModel):
    scenario: BusinessScenario
    objective: str = Field(min_length=3, max_length=2000)
    success_metrics: list[str] = Field(default_factory=list)
    constraints: list[BusinessConstraint] = Field(default_factory=list)


class ProposedAction(BusinessModel):
    action_id: UUID = Field(default_factory=uuid4)
    skill_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: ActionRisk
    requires_approval: bool = False
    idempotency_key: str = Field(min_length=1)


class BusinessExecutionPlan(BusinessModel):
    plan_id: UUID = Field(default_factory=uuid4)
    objective: BusinessObjective
    actions: list[ProposedAction] = Field(min_length=1)
    dry_run: bool = True
    estimated_tool_calls: int = Field(ge=1)
    estimated_token_budget: int = Field(ge=0)
    approval_required: bool = False

    @model_validator(mode="after")
    def financial_actions_require_approval(self) -> "BusinessExecutionPlan":
        if any(action.risk == ActionRisk.FINANCIAL_COMMITMENT for action in self.actions):
            if not self.approval_required:
                raise ValueError("financial actions require plan-level approval")
            if not all(
                action.requires_approval
                for action in self.actions
                if action.risk == ActionRisk.FINANCIAL_COMMITMENT
            ):
                raise ValueError("every financial action must require approval")
        return self


class BusinessTaskRequest(BusinessModel):
    scenario: BusinessScenario
    question: str = Field(min_length=3, max_length=5000)
    success_metrics: list[str] = Field(default_factory=list)
    constraints: list[BusinessConstraint] = Field(default_factory=list)
    dry_run: bool = True
    max_tool_calls: int = Field(default=20, ge=1, le=200)
    max_tokens: int = Field(default=24_000, ge=500, le=2_000_000)


class BusinessTaskResponse(BusinessModel):
    task_id: UUID = Field(default_factory=uuid4)
    scenario: BusinessScenario
    status: str
    plan: BusinessExecutionPlan
    safety: dict[str, Any]
    capabilities_used: list[str] = Field(default_factory=list)
