from __future__ import annotations

from eiw.retail.data import RetailDataEngine
from eiw.retail.models import (
    RetailAnalysisRequest,
    WorkstreamName,
    WorkstreamResult,
)
from eiw.retail.runtime import RetailBARuntime
from eiw.retail.supervisor import (
    OpenAICompatibleSupervisor,
    SupervisorDecision,
)


class FakeSupervisor:
    def decide(
        self,
        *,
        stage: str,
        question: str,
        completed: list[WorkstreamResult],
        max_workstreams: int,
    ) -> SupervisorDecision:
        if stage == "initial":
            return SupervisorDecision(
                workstreams=[WorkstreamName.PRODUCT],
                rationale="Product movement is the first targeted diagnostic.",
            )
        return SupervisorDecision(
            workstreams=[WorkstreamName.PROMOTION],
            rationale="Promotion is the next unresolved driver.",
        )


class FailingSupervisor:
    def decide(self, **kwargs) -> SupervisorDecision:
        raise RuntimeError("model endpoint unavailable")


def test_model_supervisor_drives_multi_wave_plan() -> None:
    runtime = RetailBARuntime(
        RetailDataEngine.demo(),
        supervisor_policy=FakeSupervisor(),
    )
    response = runtime.analyze(
        RetailAnalysisRequest(
            question="Analyze recent performance.",
            max_workstreams=3,
        )
    )

    names = [item.name for item in response.workstreams]
    assert names == [
        WorkstreamName.OVERVIEW,
        WorkstreamName.PRODUCT,
        WorkstreamName.PROMOTION,
    ]

    plan = next(event for event in response.events if event.event_type == "plan_ready")
    replan = next(
        event for event in response.events if event.event_type == "replan_ready"
    )
    assert plan.payload["planner_source"] == "model"
    assert "Product movement" in plan.payload["rationale"]
    assert replan.payload["planner_source"] == "model"


def test_model_supervisor_failure_falls_back_to_deterministic_planner() -> None:
    runtime = RetailBARuntime(
        RetailDataEngine.demo(),
        supervisor_policy=FailingSupervisor(),
    )
    response = runtime.analyze(
        RetailAnalysisRequest(
            question="Why did sales change by store and category?",
            max_workstreams=5,
        )
    )

    names = {item.name for item in response.workstreams}
    assert WorkstreamName.OVERVIEW in names
    assert WorkstreamName.STORE in names
    assert WorkstreamName.PRODUCT in names
    plan = next(event for event in response.events if event.event_type == "plan_ready")
    assert plan.payload["planner_source"] == "deterministic-fallback"


def test_supervisor_json_parser_accepts_fenced_json() -> None:
    fence = chr(96) * 3
    parsed = OpenAICompatibleSupervisor._parse_json(
        fence
        + "json\n"
        + "{\"workstreams\":[\"store\"],\"rationale\":\"inspect stores\"}"
        + "\n"
        + fence
    )
    assert parsed["workstreams"] == ["store"]
