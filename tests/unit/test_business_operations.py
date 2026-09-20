from datetime import UTC, datetime, timedelta

import pytest

from eiw.business.models import BusinessScenario, BusinessTaskRequest
from eiw.business.operations import BusinessOperationsService
from eiw.runtime.governance import RuntimeBudget
from eiw.runtime.memory import MemoryKind, MemoryRecord, MemoryStore
from eiw.runtime.skills import default_skill_registry


def test_default_skill_registry_covers_business_scenarios():
    registry = default_skill_registry()
    skill_ids = {skill.skill_id for skill in registry.list()}
    assert {
        "business.metric_analysis",
        "business.attribution",
        "business.marketing_budget",
        "business.sales_expansion",
        "business.monetization",
        "runtime.verify_action",
    } <= skill_ids


@pytest.mark.parametrize(
    ("scenario", "expected_skill"),
    [
        (BusinessScenario.ANALYTICS, "business.attribution"),
        (BusinessScenario.MARKETING_BUDGET, "business.marketing_budget"),
        (BusinessScenario.SALES_EXPANSION, "business.sales_expansion"),
        (BusinessScenario.MONETIZATION, "business.monetization"),
    ],
)
def test_business_planner_covers_all_required_scenarios(scenario, expected_skill):
    response = BusinessOperationsService().plan(
        BusinessTaskRequest(
            scenario=scenario,
            question="Create a governed business plan with evidence.",
        )
    )
    assert expected_skill in response.capabilities_used
    assert response.plan.estimated_tool_calls == len(response.plan.actions)
    assert response.safety["external_writes_executed"] is False


def test_marketing_budget_requires_human_approval_and_never_executes_in_public_reference():
    response = BusinessOperationsService().plan(
        BusinessTaskRequest(
            scenario=BusinessScenario.MARKETING_BUDGET,
            question="Allocate the remaining marketing budget across eligible segments.",
        )
    )
    financial = [action for action in response.plan.actions if action.risk.value == "FINANCIAL_COMMITMENT"]
    assert response.plan.approval_required is True
    assert response.status == "PLANNED_REQUIRES_APPROVAL"
    assert financial and all(action.requires_approval for action in financial)
    assert any("human approval required" in " ".join(check["reasons"]) for check in response.safety["checks"])


def test_runtime_budget_enforces_tool_and_token_limits():
    budget = RuntimeBudget(max_tool_calls=2, max_tokens=1000)
    budget.reserve(tool_calls=1, tokens=400)
    assert budget.remaining_tool_calls == 1
    assert budget.remaining_tokens == 600
    with pytest.raises(RuntimeError, match="tool-call budget exceeded"):
        budget.reserve(tool_calls=2)


def test_memory_store_supports_layered_memory_versioning_and_expiry():
    store = MemoryStore()
    first = store.put(MemoryRecord(key="metric.gmv", kind=MemoryKind.SEMANTIC, value={"formula": "sum(gmv)"}))
    second = store.put(MemoryRecord(key="metric.gmv", kind=MemoryKind.SEMANTIC, value={"formula": "sum(order_amount)"}))
    assert first.version == 1
    assert second.version == 2
    assert store.get(MemoryKind.SEMANTIC, "metric.gmv").value["formula"] == "sum(order_amount)"

    expired = MemoryRecord(
        key="temp",
        kind=MemoryKind.WORKING,
        value="discard",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    store.put(expired)
    assert store.get(MemoryKind.WORKING, "temp") is None
