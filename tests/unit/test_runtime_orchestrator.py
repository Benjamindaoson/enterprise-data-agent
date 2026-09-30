"""Tests for the canonical BusinessAgentRuntime application facade."""

from __future__ import annotations

from typing import Any

from eiw.business.models import BusinessScenario, BusinessTaskRequest
from eiw.runtime.long_term_memory import LongTermMemoryItem
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


class FakeLongTermMemory:
    name = "fake-memory"

    def __init__(self) -> None:
        self.retained: list[dict[str, Any]] = []

    def bank_id(self, scope: str) -> str:
        return f"bank:{scope}"

    def recall(
        self,
        scope: str,
        query: str,
        *,
        tags: tuple[str, ...] = (),
    ) -> list[LongTermMemoryItem]:
        return [
            LongTermMemoryItem(
                memory_id="memory-1",
                text="Prior analysis found store contribution useful.",
                memory_type="observation",
            )
        ]

    def retain(
        self,
        scope: str,
        content: str,
        *,
        context: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: tuple[str, ...] = (),
    ) -> None:
        self.retained.append(
            {
                "scope": scope,
                "content": content,
                "context": context,
                "tags": tags,
            }
        )

    def reflect(self, scope: str, query: str) -> str:
        return "Reuse contribution analysis before anomaly scans."


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


def test_long_term_memory_is_recalled_into_context_and_result_is_retained() -> None:
    analysis = FakeAnalysisService()
    memory = FakeLongTermMemory()
    runtime = BusinessAgentRuntime(
        analysis_service=analysis,
        long_term_memory=memory,
    )

    runtime.analyze(
        "Why did sales change?",
        {
            "tenant_id": "tenant-1",
            "user_id": "analyst-1",
        },
    )

    recalled = analysis.calls[0]["user_context"]["long_term_memory"]
    assert recalled[0]["memory_id"] == "memory-1"
    assert memory.retained
    assert memory.retained[0]["scope"] == "tenant:tenant-1:user:analyst-1"
    assert runtime.reflect_long_term_memory(
        "What should we reuse?",
        user_context={"tenant_id": "tenant-1", "user_id": "analyst-1"},
    ).startswith("Reuse contribution")


def test_feedback_is_retained_as_long_term_learning_signal() -> None:
    memory = FakeLongTermMemory()
    runtime = BusinessAgentRuntime(
        analysis_service=FakeAnalysisService(),
        long_term_memory=memory,
    )

    runtime.record_feedback(
        task_id="task-123",
        rating=2,
        comment="The store diagnosis missed the main driver.",
        user_context={"tenant_id": "tenant-1", "user_id": "analyst-1"},
    )

    retained = memory.retained[-1]
    assert retained["scope"] == "tenant:tenant-1:user:analyst-1"
    assert "rating" in retained["content"]
    assert retained["tags"] == ("feedback", "analysis", "rating:2")


def test_domain_memory_scope_is_tenant_and_user_isolated() -> None:
    request = type(
        "Request",
        (),
        {"tenant_id": "tenant-a", "user_id": "user-b"},
    )()

    scope = BusinessAgentRuntime._domain_memory_scope("retail", request)

    assert scope == "domain:retail:tenant:tenant-a:user:user-b"
