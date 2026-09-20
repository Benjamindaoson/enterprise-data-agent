"""Scenario-aware planner for business intelligence and autonomous operations.

The public reference implementation intentionally emits dry-run/proposal actions for
external CRM, campaign and monetization systems. This proves the agent contract,
governance and approval boundaries without claiming proprietary integrations.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

from eiw.business.models import (
    ActionRisk,
    BusinessExecutionPlan,
    BusinessObjective,
    BusinessScenario,
    BusinessTaskRequest,
    BusinessTaskResponse,
    ProposedAction,
)
from eiw.runtime.governance import ActionPolicy, RuntimeBudget
from eiw.runtime.skills import SkillRegistry, default_skill_registry


class BusinessOperationsService:
    def __init__(self, skills: SkillRegistry | None = None) -> None:
        self.skills = skills or default_skill_registry()

    @staticmethod
    def _key(question: str, skill_id: str, ordinal: int) -> str:
        payload = f"{question}|{skill_id}|{ordinal}".encode()
        return hashlib.sha256(payload).hexdigest()[:24]

    def _action(
        self,
        *,
        request: BusinessTaskRequest,
        ordinal: int,
        skill_id: str,
        description: str,
        tool_name: str,
        risk: ActionRisk = ActionRisk.READ_ONLY,
        parameters: dict[str, object] | None = None,
    ) -> ProposedAction:
        return ProposedAction(
            skill_id=skill_id,
            description=description,
            tool_name=tool_name,
            parameters=parameters or {},
            risk=risk,
            requires_approval=risk == ActionRisk.FINANCIAL_COMMITMENT,
            idempotency_key=self._key(request.question, skill_id, ordinal),
        )

    def plan(self, request: BusinessTaskRequest) -> BusinessTaskResponse:
        objective = BusinessObjective(
            scenario=request.scenario,
            objective=request.question,
            success_metrics=request.success_metrics,
            constraints=request.constraints,
        )
        actions = self._scenario_actions(request)
        budget = RuntimeBudget(
            max_tool_calls=request.max_tool_calls,
            max_tokens=request.max_tokens,
        )
        estimated_tokens = 1200 + (700 * len(actions))
        budget.reserve(tool_calls=len(actions), tokens=estimated_tokens)

        approval_required = any(
            action.risk == ActionRisk.FINANCIAL_COMMITMENT for action in actions
        )
        plan = BusinessExecutionPlan(
            objective=objective,
            actions=actions,
            dry_run=request.dry_run,
            estimated_tool_calls=len(actions),
            estimated_token_budget=estimated_tokens,
            approval_required=approval_required,
        )

        policy = ActionPolicy(
            permissions={
                "analytics:read",
                "marketing:read",
                "marketing:propose",
                "sales:read",
                "crm:propose",
                "monetization:read",
                "monetization:propose",
                "runtime:verify",
            },
            allow_financial_execution=False,
        )
        safety_checks = [
            policy.evaluate(action, required_permissions=set(self.skills.get(action.skill_id).permissions))
            for action in actions
        ]
        return BusinessTaskResponse(
            task_id=uuid4(),
            scenario=request.scenario,
            status="PLANNED_REQUIRES_APPROVAL" if approval_required else "PLANNED",
            plan=plan,
            safety={
                "dry_run": request.dry_run,
                "checks": safety_checks,
                "remaining_tool_calls": budget.remaining_tool_calls,
                "remaining_tokens": budget.remaining_tokens,
                "external_writes_executed": False,
            },
            capabilities_used=sorted({action.skill_id for action in actions}),
        )

    def _scenario_actions(self, request: BusinessTaskRequest) -> list[ProposedAction]:
        if request.scenario == BusinessScenario.ANALYTICS:
            return [
                self._action(
                    request=request,
                    ordinal=1,
                    skill_id="business.metric_analysis",
                    description="Resolve business semantics and establish the governed metric baseline.",
                    tool_name="semantic_layer",
                ),
                self._action(
                    request=request,
                    ordinal=2,
                    skill_id="business.attribution",
                    description="Perform multi-dimensional drill-down and rank observed contributors.",
                    tool_name="contribution_analysis",
                ),
                self._action(
                    request=request,
                    ordinal=3,
                    skill_id="runtime.verify_action",
                    description="Verify claims against evidence before presenting findings.",
                    tool_name="verification",
                ),
            ]
        if request.scenario == BusinessScenario.MARKETING_BUDGET:
            return [
                self._action(
                    request=request,
                    ordinal=1,
                    skill_id="business.metric_analysis",
                    description="Measure historical campaign performance and governed ROI metrics.",
                    tool_name="campaign_history",
                ),
                self._action(
                    request=request,
                    ordinal=2,
                    skill_id="business.marketing_budget",
                    description="Generate a constrained budget-allocation proposal and scenario simulation.",
                    tool_name="optimizer",
                ),
                self._action(
                    request=request,
                    ordinal=3,
                    skill_id="business.marketing_budget",
                    description="Prepare the approved allocation for the campaign system.",
                    tool_name="campaign_api",
                    risk=ActionRisk.FINANCIAL_COMMITMENT,
                ),
            ]
        if request.scenario == BusinessScenario.SALES_EXPANSION:
            return [
                self._action(
                    request=request,
                    ordinal=1,
                    skill_id="business.sales_expansion",
                    description="Build the eligible merchant/account universe and opportunity features.",
                    tool_name="merchant_profile",
                ),
                self._action(
                    request=request,
                    ordinal=2,
                    skill_id="business.sales_expansion",
                    description="Rank leads with evidence and capacity constraints.",
                    tool_name="opportunity_ranker",
                ),
                self._action(
                    request=request,
                    ordinal=3,
                    skill_id="business.sales_expansion",
                    description="Prepare prioritized leads for CRM handoff.",
                    tool_name="crm",
                    risk=ActionRisk.REVERSIBLE_WRITE,
                ),
            ]
        if request.scenario == BusinessScenario.MONETIZATION:
            return [
                self._action(
                    request=request,
                    ordinal=1,
                    skill_id="business.monetization",
                    description="Identify eligible merchant monetization opportunities.",
                    tool_name="merchant_profile",
                ),
                self._action(
                    request=request,
                    ordinal=2,
                    skill_id="business.monetization",
                    description="Match products and simulate expected revenue under constraints.",
                    tool_name="revenue_simulator",
                ),
                self._action(
                    request=request,
                    ordinal=3,
                    skill_id="runtime.verify_action",
                    description="Verify evidence, permissions and recommendation limits.",
                    tool_name="verification",
                ),
            ]
        raise ValueError(f"unsupported scenario: {request.scenario}")
