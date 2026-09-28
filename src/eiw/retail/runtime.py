"""Autonomous multi-workstream retail Business Analysis runtime."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from uuid import uuid4

from eiw.retail.charts import ChartPlanner
from eiw.retail.data import RetailDataEngine
from eiw.retail.insight import InsightMiner
from eiw.retail.models import (
    RetailAnalysisRequest,
    RetailAnalysisResponse,
    RuntimeEvent,
    WorkstreamName,
    WorkstreamResult,
)
from eiw.retail.planner import InvestigationPlanner
from eiw.retail.report import RetailReportBuilder
from eiw.retail.skills import RetailAnalyticalWorkers

EventCallback = Callable[[RuntimeEvent], None]


class RetailBARuntime:
    """Supervisor + typed analytical worker runtime.

    The public event stream exposes actions and results, never private chain-of-thought.
    """

    def __init__(self, data: RetailDataEngine) -> None:
        self.data = data
        self.planner = InvestigationPlanner()
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

        def emit(
            event_type: str,
            message: str,
            *,
            workstream: WorkstreamName | None = None,
            progress: float | None = None,
            payload: dict[str, object] | None = None,
        ) -> None:
            event = RuntimeEvent(
                event_type=event_type,
                message=message,
                workstream=workstream.value if workstream else None,
                progress=progress,
                payload=dict(payload or {}),
            )
            events.append(event)
            if on_event:
                on_event(event)

        current, previous = self._periods(request)
        emit(
            "analysis_started",
            "Business question accepted; building the investigation plan.",
            progress=0.02,
            payload={"current_weeks": current, "previous_weeks": previous},
        )
        plan = self.planner.plan(request)
        emit(
            "plan_ready",
            f"Launching {len(plan)} analytical workstreams.",
            progress=0.08,
            payload={"workstreams": [item.value for item in plan]},
        )

        workstream_started = perf_counter()
        results: list[WorkstreamResult] = []
        with ThreadPoolExecutor(max_workers=max(1, len(plan))) as executor:
            futures = {}
            for name in plan:
                emit(
                    "workstream_started",
                    f"{name.value.title()} analysis started.",
                    workstream=name,
                    progress=0.10,
                )
                futures[executor.submit(self.workers.run, name, current, previous)] = name

            for finished, future in enumerate(as_completed(futures), start=1):
                name = futures[future]
                result = future.result()
                results.append(result)
                emit(
                    "workstream_completed",
                    result.summary,
                    workstream=name,
                    progress=0.10 + 0.45 * finished / len(plan),
                    payload={"row_count": len(result.rows)},
                )

        results.sort(key=lambda item: plan.index(item.name))
        workstream_ms = (perf_counter() - workstream_started) * 1000.0

        overview = next((item for item in results if item.name == WorkstreamName.OVERVIEW), None)
        kpis = dict(overview.metrics) if overview else {}
        emit("insight_mining_started", "Scanning analytical results for high-impact findings.", progress=0.60)
        insight_started = perf_counter()
        insights = self.insights.mine(results, top_k=request.top_k)
        insight_ms = (perf_counter() - insight_started) * 1000.0
        emit(
            "insights_ready",
            f"Ranked {len(insights)} business findings.",
            progress=0.72,
            payload={"insight_ids": [item.insight_id for item in insights]},
        )

        chart_started = perf_counter()
        charts = self.charts.plan(results, insights)
        chart_ms = (perf_counter() - chart_started) * 1000.0
        emit(
            "charts_ready",
            f"Prepared {len(charts)} decision-oriented chart specifications.",
            progress=0.84,
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
            kpis=kpis,
            workstreams=results,
            insights=insights,
            charts=charts,
            report=report,
            events=events,
            timings_ms={
                "workstreams": round(workstream_ms, 3),
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
