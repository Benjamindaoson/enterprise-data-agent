"""LangGraph investigation loop for the retail BA Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from eiw.retail.models import (
    BusinessQuestionContext,
    RetailAnalysisRequest,
    RuntimeEvent,
    WorkstreamName,
    WorkstreamResult,
)
from eiw.retail.planner import InvestigationPlanner
from eiw.retail.semantics import RetailSemanticEngine
from eiw.retail.skills import RetailAnalyticalWorkers
from eiw.retail.team import RetailAnalysisTeam, SpecialistProfile

EventEmitter = Callable[[RuntimeEvent], None]


class RetailGraphState(TypedDict, total=False):
    request: RetailAnalysisRequest
    current_weeks: list[int]
    previous_weeks: list[int]
    semantics: BusinessQuestionContext
    initial_plan: list[WorkstreamName]
    follow_up_plan: list[WorkstreamName]
    results: list[WorkstreamResult]


class RetailInvestigationGraph:
    """Explicit production graph for semantics → plan → execute → replan."""

    def __init__(
        self,
        workers: RetailAnalyticalWorkers,
        *,
        emit: EventEmitter,
        planner: InvestigationPlanner | None = None,
        semantic_engine: RetailSemanticEngine | None = None,
    ) -> None:
        self.semantic = semantic_engine or RetailSemanticEngine()
        self.planner = planner or InvestigationPlanner()
        self.team = RetailAnalysisTeam(workers)
        self.emit = emit
        self._graph = self._compile()

    def _compile(self):
        builder = StateGraph(RetailGraphState)
        builder.add_node("resolve_semantics", self._resolve_semantics)
        builder.add_node("plan_initial", self._plan_initial)
        builder.add_node("run_initial", self._run_initial)
        builder.add_node("replan", self._replan)
        builder.add_node("run_follow_up", self._run_follow_up)

        builder.add_edge(START, "resolve_semantics")
        builder.add_edge("resolve_semantics", "plan_initial")
        builder.add_edge("plan_initial", "run_initial")
        builder.add_edge("run_initial", "replan")
        builder.add_conditional_edges(
            "replan",
            self._route_after_replan,
            {
                "follow_up": "run_follow_up",
                "finish": END,
            },
        )
        builder.add_edge("run_follow_up", END)
        return builder.compile()

    def run(
        self,
        request: RetailAnalysisRequest,
        *,
        current_weeks: list[int],
        previous_weeks: list[int],
    ) -> RetailGraphState:
        state = self._graph.invoke(
            {
                "request": request,
                "current_weeks": current_weeks,
                "previous_weeks": previous_weeks,
                "results": [],
            }
        )
        return RetailGraphState(**state)

    def _resolve_semantics(self, state: RetailGraphState) -> dict[str, Any]:
        context = self.semantic.resolve(state["request"])
        self.emit(
            RuntimeEvent(
                event_type="semantics_resolved",
                message="Business semantics resolved into metrics, dimensions and analytical intents.",
                progress=0.05,
                payload=context.model_dump(mode="json"),
            )
        )
        return {"semantics": context}

    def _plan_initial(self, state: RetailGraphState) -> dict[str, Any]:
        plan = self.planner.initial_plan(state["request"])
        self.emit(
            RuntimeEvent(
                event_type="plan_ready",
                message=f"Launching the first wave with {len(plan)} specialist workstreams.",
                progress=0.08,
                payload={
                    "workstreams": [item.value for item in plan],
                    "wave": 1,
                    "planner_source": self.planner.last_source,
                    "rationale": self.planner.last_rationale,
                },
            )
        )
        return {"initial_plan": plan}

    def _run_initial(self, state: RetailGraphState) -> dict[str, Any]:
        results = self._run_wave(
            state["initial_plan"],
            state["current_weeks"],
            state["previous_weeks"],
            wave=1,
            question=state["request"].question,
        )
        return {"results": results}

    def _replan(self, state: RetailGraphState) -> dict[str, Any]:
        self.emit(
            RuntimeEvent(
                event_type="replan_started",
                message="Supervisor is deciding whether another analytical wave is warranted.",
                progress=0.50,
            )
        )
        follow_up = self.planner.replan(state["request"], state.get("results", []))
        if follow_up:
            self.emit(
                RuntimeEvent(
                    event_type="replan_ready",
                    message=f"Launching {len(follow_up)} additional specialist workstreams.",
                    progress=0.53,
                    payload={
                        "workstreams": [item.value for item in follow_up],
                        "wave": 2,
                        "planner_source": self.planner.last_source,
                        "rationale": self.planner.last_rationale,
                    },
                )
            )
        else:
            self.emit(
                RuntimeEvent(
                    event_type="replan_skipped",
                    message="Current analysis is sufficient; no additional workstream is required.",
                    progress=0.53,
                    payload={
                        "planner_source": self.planner.last_source,
                        "rationale": self.planner.last_rationale,
                    },
                )
            )
        return {"follow_up_plan": follow_up}

    def _route_after_replan(self, state: RetailGraphState) -> str:
        return "follow_up" if state.get("follow_up_plan") else "finish"

    def _run_follow_up(self, state: RetailGraphState) -> dict[str, Any]:
        extra = self._run_wave(
            state.get("follow_up_plan", []),
            state["current_weeks"],
            state["previous_weeks"],
            wave=2,
            question=state["request"].question,
        )
        return {"results": [*state.get("results", []), *extra]}

    def _run_wave(
        self,
        names: list[WorkstreamName],
        current: list[int],
        previous: list[int],
        *,
        wave: int,
        question: str,
    ) -> list[WorkstreamResult]:
        completed = 0

        def started(profile: SpecialistProfile) -> None:
            self.emit(
                RuntimeEvent(
                    event_type="workstream_started",
                    message=f"{profile.name} started: {profile.mission}",
                    workstream=profile.workstream.value,
                    progress=0.10 if wave == 1 else 0.54,
                    payload={"specialist": profile.name, "wave": wave},
                )
            )

        def finished(profile: SpecialistProfile, result: WorkstreamResult) -> None:
            nonlocal completed
            completed += 1
            base = 0.12 if wave == 1 else 0.55
            ceiling = 0.48 if wave == 1 else 0.62
            progress = min(ceiling, base + (ceiling - base) * completed / max(1, len(names)))
            self.emit(
                RuntimeEvent(
                    event_type="workstream_completed",
                    message=result.summary,
                    workstream=profile.workstream.value,
                    progress=progress,
                    payload={
                        "specialist": profile.name,
                        "row_count": len(result.rows),
                        "metrics": result.metrics,
                        "wave": wave,
                        "policy_source": result.metadata.get("policy_source"),
                        "selected_skills": result.metadata.get(
                            "selected_skills",
                            [],
                        ),
                        "rationale": result.metadata.get("rationale", ""),
                    },
                )
            )

        return self.team.run_wave(
            names,
            current,
            previous,
            question=question,
            on_started=started,
            on_completed=finished,
        )
