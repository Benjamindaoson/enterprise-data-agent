"""Tests for the canonical BusinessAgentRuntime application facade."""

from __future__ import annotations

from typing import Any

from eiw.business.models import BusinessScenario, BusinessTaskRequest
from eiw.runtime.memory import MemoryKind
from eiw.runtime.orchestrator import BusinessAgentRuntime


class FakeAnalysisService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(
        self,
        question: str,
        user_context: dict[str, Any],
        lineage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "question": question,
                "user_context": user_context,
                "lineage": lineage,
            }
        )
        return {
            "task_id": "task-123",
            "state": "COMPLETED",
            "claims": [{"claim_id": "claim-1"}],
            "evidence": [{"evidence_id": "evidence-1"}],
        }


class FakeStore:
    def __init__(self, task: dict[str, Any] | None) -> None:
        self.task = task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        if self.task is None or self.task.get("task_id") != task_id:
            return None
        return self.task


class FakeProductionStore:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def append_trajectory_event(self, **event: Any) -> str:
        self.events.append(event)
        return f"event-{len(self.events)}"


def test_capabilities_come_from_canonical_runtime() -> None:
    runtime = BusinessAgentRuntime(analysis_service=FakeAnalysisService())

    capabilities = runtime.capabilities()

    assert capabilities["runtime"]["name"] == "BusinessAgentRuntime"
    assert "Runtime -> Skill/AnalyticalLane" in capabilities["runtime"]["canonical_path"]
    assert capabilities["runtime"]["analysis_lane"] == "deterministic_semantic_analytics"
    assert capabilities["public_reference_limits"]["real_campaign_crm_integrations"] is False


def test_analysis_runs_through_runtime_and_records_episodic_memory() -> None:
    analysis = FakeAnalysisService()
    runtime = BusinessAgentRuntime(analysis_service=analysis)

    result = runtime.analyze(
        "Compare sales by region",
        {"user_id": "analyst-1", "roles": ["business_analyst"]},
    )

    assert result["runtime"]["runtime_name"] == "BusinessAgentRuntime"
    assert result["runtime"]["lane"] == "deterministic_semantic_analytics"
    assert analysis.calls[0]["question"] == "Compare sales by region"

    memory = runtime.memory.get(MemoryKind.EPISODIC, "analysis:task-123")
    assert memory is not None
    assert memory.value["claim_ids"] == ["claim-1"]
    assert memory.value["evidence_ids"] == ["evidence-1"]

    events = runtime.events()
    assert [event["event_type"] for event in events] == [
        "RUNTIME_STARTED",
        "RUNTIME_COMPLETED",
    ]


def test_follow_up_preserves_explicit_lineage() -> None:
    analysis = FakeAnalysisService()
    runtime = BusinessAgentRuntime(analysis_service=analysis)
    store = FakeStore(
        {
            "task_id": "parent-1",
            "user_context": {"user_id": "analyst-1"},
            "resolved_context": {"context_version": "ctx-v7"},
        }
    )

    runtime.follow_up(
        parent_task_id="parent-1",
        question="Drill into the top contributor",
        referenced_evidence_ids=["evidence-7"],
        store=store,
    )

    lineage = analysis.calls[0]["lineage"]
    assert lineage == {
        "parent_task_id": "parent-1",
        "reused_evidence_ids": ["evidence-7"],
        "parent_context_version": "ctx-v7",
    }


def test_business_task_uses_same_runtime_and_records_memory() -> None:
    runtime = BusinessAgentRuntime(analysis_service=FakeAnalysisService())
    request = BusinessTaskRequest(
        scenario=BusinessScenario.ANALYTICS,
        question="Explain the monthly sales decline",
    )

    response = runtime.plan_business_task(request)

    assert response.scenario == BusinessScenario.ANALYTICS
    assert response.capabilities_used
    memory = runtime.memory.get(
        MemoryKind.EPISODIC,
        f"business-task:{response.task_id}",
    )
    assert memory is not None
    assert memory.value["scenario"] == "ANALYTICS"


def test_completed_runtime_event_is_persisted_when_production_store_is_configured() -> None:
    production = FakeProductionStore()
    runtime = BusinessAgentRuntime(
        analysis_service=FakeAnalysisService(),
        production_store=production,
    )

    runtime.analyze("Compare sales by region", {"user_id": "analyst-1"})

    assert len(production.events) == 1
    event = production.events[0]
    assert event["trajectory_id"] == "runtime:task-123"
    assert event["task_id"] == "task-123"
    assert event["step_index"] == 0
    assert event["payload"]["event_type"] == "RUNTIME_COMPLETED"



class FakeDomainResponse:
    def __init__(self) -> None:
        self.task_id = "domain-task-1"
        self.status = "COMPLETED"


class FakeDomainRuntime:
    domain_id = "retail"

    def __init__(self) -> None:
        self.requests: list[Any] = []

    def capabilities(self) -> dict[str, Any]:
        return {"runtime": "fake-retail"}

    def analyze(self, request: Any, *, on_event: Any = None) -> FakeDomainResponse:
        self.requests.append(request)
        if on_event is not None:
            on_event({"event_type": "fake"})
        return FakeDomainResponse()


def test_domain_runtime_is_hosted_by_business_agent_runtime() -> None:
    domain = FakeDomainRuntime()
    runtime = BusinessAgentRuntime(
        analysis_service=None,
        domain_runtimes=[domain],
    )

    observed: list[Any] = []
    result = runtime.analyze_domain(
        "retail",
        {"question": "why did sales decline?"},
        on_event=observed.append,
    )

    assert result.status == "COMPLETED"
    assert domain.requests == [{"question": "why did sales decline?"}]
    assert observed == [{"event_type": "fake"}]
    assert runtime.capabilities()["domains"]["retail"]["runtime"] == "fake-retail"
    assert [event["event_type"] for event in runtime.events()] == [
        "DOMAIN_RUNTIME_STARTED",
        "DOMAIN_RUNTIME_COMPLETED",
    ]


def test_domain_only_runtime_rejects_generic_lane() -> None:
    runtime = BusinessAgentRuntime(analysis_service=None)

    try:
        runtime.analyze("question", {})
    except RuntimeError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("expected generic lane to fail closed")
