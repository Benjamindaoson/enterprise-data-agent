"""Autonomous LangGraph retail Business Analysis runtime."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from uuid import uuid4

from eiw.retail.charts import ChartPlanner
from eiw.retail.data import RetailDataEngine
from eiw.retail.graph import RetailInvestigationGraph
from eiw.retail.insight import InsightMiner
from eiw.retail.models import RetailAnalysisRequest, RetailAnalysisResponse, RuntimeEvent, WorkstreamName
from eiw.retail.report import RetailReportBuilder
from eiw.retail.skills import RetailAnalyticalWorkers

EventCallback = Callable[[RuntimeEvent], None]


class RetailBARuntime:
    """Production-facing BA runtime built around an explicit LangGraph loop."""

    def __init__(self, data: RetailDataEngine) -> None:
        self.data = data
        self.workers = RetailAnalyticalWorkers(data)
        self.insights = InsightMiner()
        self.charts = ChartPlanner()
        self.reports = RetailReportBuilder()

    def analyze(
        self,
        request: RetailAnalysisRequest,
        *,
        on_event: EventCallback | None = None,
    ) -> RetailAnalysisResponse:
        started = perf_counter()
        task_id = f"retail-{uuid4().hex[:12]}"
        events: list[RuntimeEvent] = []

        def record(event: RuntimeEvent) -> None:
            events.append(event)
            if on_event:
                on_event(event)

        def emit(
            event_type: str,
            message: str,
            *,
            progress: float | None = None,
            payload: dict[str, object] | None = None,
        ) -> None:
            record(
                RuntimeEvent(
                    event_type=event_type,
                    message=message,
                    progress=progress,
                    payload=dict(payload or {}),
                )
            )

        current, previous = self._periods(request)
        emit(
            "analysis_started",
            "Business question accepted; starting the autonomous investigation graph.",
            progress=0.02,
            payload={"current_weeks": current, "previous_weeks": previous},
        )

        graph_started = perf_counter()
        graph = RetailInvestigationGraph(self.workers, emit=record)
        graph_state = graph.run(
            request,
            current_weeks=current,
            previous_weeks=previous,
        )
        graph_ms = (perf_counter() - graph_started) * 1000.0

        semantics = graph_state["semantics"]
        results = graph_state.get("results", [])
        overview = next((item for item in results if item.name == WorkstreamName.OVERVIEW), None)
        kpis = dict(overview.metrics) if overview else {}

        emit(
            "insight_mining_started",
            "Scanning analytical results for high-impact findings.",
            progress=0.66,
        )
        insight_started = perf_counter()
        insights = self.insights.mine(results, top_k=request.top_k)
        insight_ms = (perf_counter() - insight_started) * 1000.0
        emit(
            "insights_ready",
            f"Ranked {len(insights)} business findings.",
            progress=0.76,
            payload={"insight_ids": [item.insight_id for item in insights]},
        )

        chart_started = perf_counter()
        charts = self.charts.plan(results, insights)
        chart_ms = (perf_counter() - chart_started) * 1000.0
        emit(
            "charts_ready",
            f"Prepared {len(charts)} decision-oriented chart specifications.",
            progress=0.87,
        )

        report_started = perf_counter()
        report = self.reports.build(
            question=request.question,
            kpis=kpis,
            workstreams=results,
            insights=insights,
        )
        report_ms = (perf_counter() - report_started) * 1000.0
        emit(
            "report_ready",
            "Executive business review assembled.",
            progress=0.97,
            payload={"action_count": len(report.actions)},
        )
        total_ms = (perf_counter() - started) * 1000.0
        emit(
            "analysis_completed",
            f"Analysis completed in {total_ms:.0f} ms.",
            progress=1.0,
        )

        return RetailAnalysisResponse(
            task_id=task_id,
            status="COMPLETED",
            dataset=self.data.status(),
            question=request.question,
            current_weeks=current,
            previous_weeks=previous,
            semantics=semantics,
            kpis=kpis,
            workstreams=results,
            insights=insights,
            charts=charts,
            report=report,
            events=events,
            timings_ms={
                "investigation_graph": round(graph_ms, 3),
                "insight_mining": round(insight_ms, 3),
                "chart_planning": round(chart_ms, 3),
                "report": round(report_ms, 3),
                "total": round(total_ms, 3),
            },
        )

    def _periods(self, request: RetailAnalysisRequest) -> tuple[list[int], list[int]]:
        if request.current_weeks and request.previous_weeks:
            return request.current_weeks, request.previous_weeks
        current, previous = self.data.week_bounds()
        return request.current_weeks or current, request.previous_weeks or previous
