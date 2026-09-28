"""FastAPI router for the retail BA Agent reference vertical."""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from eiw.production.persistence import ProductionStore
from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.charts import ChartPlanner
from eiw.retail.code_analysis import RetailCodeAnalyst
from eiw.retail.code_worker import (
    DockerCodeSandbox,
    FirstPartyRetailCodeAnalyst,
    OpenAICompatibleCodeGenerator,
)
from eiw.retail.domain import RetailDomainRuntime, build_retail_domain_runtime
from eiw.retail.export import render_report_html, render_report_pdf
from eiw.retail.models import (
    ChartRestyleRequest,
    CodeAnalysisRequest,
    RetailAnalysisRequest,
    RetailAnalysisResponse,
    RuntimeEvent,
)
from eiw.retail.upstream import DeepAnalyzeWorker
from eiw.runtime.domain import DomainRuntimeError
from eiw.runtime.orchestrator import BusinessAgentRuntime


def create_retail_router(
    *,
    runtime: BusinessAgentRuntime | None = None,
    production_store: ProductionStore | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/ba/retail", tags=["ba-retail"])
    business_runtime = runtime or BusinessAgentRuntime(
        analysis_service=None,
        production_store=production_store,
    )
    if not business_runtime.has_domain("retail"):
        business_runtime.register_domain(build_retail_domain_runtime())
    domain = cast(
        RetailDomainRuntime,
        business_runtime.domain_runtime("retail"),
    )
    retail_agent = domain.agent
    history: dict[str, RetailAnalysisResponse] = {}
    history_lock = threading.Lock()

    def remember(response: RetailAnalysisResponse) -> None:
        with history_lock:
            history[response.task_id] = response
            while len(history) > 100:
                history.pop(next(iter(history)))
        if production_store is not None:
            production_store.save_checkpoint(
                task_id=response.task_id,
                version=1,
                payload={
                    "kind": "retail_analysis_response",
                    "response": response.model_dump(mode="json"),
                },
            )

    def load_response(task_id: str) -> RetailAnalysisResponse | None:
        with history_lock:
            response = history.get(task_id)
        if response is not None:
            return response
        if production_store is None:
            return None
        checkpoint = production_store.load_checkpoint(task_id)
        if checkpoint is None:
            return None
        payload = checkpoint.get("payload") or {}
        if payload.get("kind") != "retail_analysis_response":
            return None
        raw = payload.get("response")
        if not isinstance(raw, dict):
            return None
        restored = RetailAnalysisResponse.model_validate(raw)
        with history_lock:
            history[restored.task_id] = restored
        return restored

    def inherit(request: RetailAnalysisRequest) -> RetailAnalysisRequest:
        if not request.parent_task_id:
            return request
        parent = load_response(request.parent_task_id)
        if parent is None:
            raise HTTPException(404, "Parent retail analysis task not found")
        updates: dict[str, object] = {}
        if not request.current_weeks:
            updates["current_weeks"] = list(parent.current_weeks)
        if not request.previous_weeks:
            updates["previous_weeks"] = list(parent.previous_weeks)
        return request.model_copy(update=updates)

    @router.get("/status")
    def status() -> dict[str, object]:
        return {
            "product": "Business Analysis Agent",
            "vertical": "Retail Intelligence",
            "dataset": domain.data.status(),
            "mode": "real-data" if not domain.data.label.startswith("retail-demo") else "deterministic-demo",
        }

    @router.get("/capabilities")
    @router.get("/upstreams")
    def capabilities() -> dict[str, object]:
        deep_url = os.getenv("EIW_DEEPANALYZE_URL", "").strip()
        deep = DeepAnalyzeWorker(base_url=deep_url) if deep_url else None
        code_url = os.getenv("EIW_RETAIL_CODE_MODEL_URL", "").strip()
        supervisor_url = os.getenv("EIW_RETAIL_SUPERVISOR_URL", "").strip()
        specialist_url = os.getenv("EIW_RETAIL_SPECIALIST_URL", "").strip()
        sandbox = DockerCodeSandbox()
        return {
            "runtime": "first-party",
            "business_semantic_engine": "first-party",
            "multi_agent_supervisor": {
                "mode": "model" if supervisor_url else "deterministic",
                "model_base_url": supervisor_url or None,
                "fallback": "deterministic",
            },
            "specialist_agents": {
                "mode": "model" if specialist_url else "deterministic",
                "model_base_url": specialist_url or None,
                "fallback": "deterministic-full-skill-set",
            },
            "analytical_skills": "first-party",
            "insight_mining": "first-party",
            "visualization_and_reporting": "first-party",
            "first_party_code_worker": {
                "configured": bool(code_url),
                "docker_available": sandbox.available(),
                "model_base_url": code_url or None,
                "model": (
                    os.getenv("EIW_RETAIL_CODE_MODEL", "qwen3")
                    if code_url
                    else None
                ),
            },
            "external_compatibility": {
                "deepanalyze": {
                    "configured": bool(deep_url),
                    "healthy": deep.health() if deep else False,
                    "base_url": deep_url or None,
                    "role": "optional external fallback",
                }
            },
        }

    @router.post("/analyze")
    def analyze(request: RetailAnalysisRequest) -> dict[str, object]:
        resolved = inherit(request)
        try:
            response = cast(
                RetailAnalysisResponse,
                business_runtime.analyze_domain("retail", resolved),
            )
        except DomainRuntimeError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        remember(response)
        return response.model_dump(mode="json")

    @router.get("/runs/{task_id}")
    def get_run(task_id: str) -> dict[str, object]:
        response = load_response(task_id)
        if response is None:
            raise HTTPException(404, "Retail analysis task not found")
        return response.model_dump(mode="json")

    @router.post("/analyze/stream")
    def analyze_stream(request: RetailAnalysisRequest) -> StreamingResponse:
        resolved = inherit(request)
        channel: queue.Queue[dict[str, object] | None] = queue.Queue()

        def emit(event: RuntimeEvent) -> None:
            channel.put({"kind": "event", "payload": event.model_dump(mode="json")})

        def run() -> None:
            try:
                response = cast(
                    RetailAnalysisResponse,
                    business_runtime.analyze_domain(
                        "retail",
                        resolved,
                        on_event=cast(Any, emit),
                    ),
                )
                remember(response)
                channel.put({"kind": "result", "payload": response.model_dump(mode="json")})
            except DomainRuntimeError as exc:
                channel.put(
                    {
                        "kind": "error",
                        "payload": {
                            "message": str(exc),
                            "code": exc.code,
                            "status_code": exc.status_code,
                        },
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive API boundary
                channel.put({"kind": "error", "payload": {"message": str(exc)}})
            finally:
                channel.put(None)

        threading.Thread(target=run, daemon=True, name="retail-ba-analysis").start()

        def stream() -> Iterator[str]:
            while True:
                item = channel.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.post("/code-analysis")
    def code_analysis(request: CodeAnalysisRequest) -> dict[str, object]:
        default_current, default_previous = domain.data.week_bounds()
        current = request.current_weeks or default_current
        previous = request.previous_weeks or default_previous

        code_url = os.getenv("EIW_RETAIL_CODE_MODEL_URL", "").strip()
        if code_url:
            sandbox = DockerCodeSandbox()
            if not sandbox.available():
                raise HTTPException(
                    status_code=503,
                    detail="Docker is required for the first-party code-analysis sandbox",
                )
            generator = OpenAICompatibleCodeGenerator(
                base_url=code_url,
                model=os.getenv("EIW_RETAIL_CODE_MODEL", "qwen3"),
                api_key=os.getenv("EIW_RETAIL_CODE_MODEL_API_KEY", ""),
            )
            analyst = FirstPartyRetailCodeAnalyst(domain.data, generator, sandbox)
            return analyst.analyze(
                request.instruction,
                current_weeks=current,
                previous_weeks=previous,
                max_rows=request.max_rows,
            )

        deep_url = os.getenv("EIW_DEEPANALYZE_URL", "").strip()
        if deep_url:
            worker = DeepAnalyzeWorker(base_url=deep_url)
            if not worker.health():
                raise HTTPException(
                    status_code=503,
                    detail="DeepAnalyze API is unavailable",
                )
            analyst = RetailCodeAnalyst(domain.data, worker)
            return analyst.analyze(
                request.instruction,
                current_weeks=current,
                previous_weeks=previous,
                max_rows=request.max_rows,
            )

        raise HTTPException(
            status_code=503,
            detail=(
                "Configure EIW_RETAIL_CODE_MODEL_URL for the first-party code worker "
                "or EIW_DEEPANALYZE_URL for the bootstrap fallback"
            ),
        )

    @router.post("/charts/restyle")
    def restyle_chart(request: ChartRestyleRequest) -> dict[str, object]:
        chart = ChartPlanner().restyle(request.chart, request.instruction)
        return chart.model_dump(mode="json")

    @router.post("/report/html", response_class=HTMLResponse)
    def report_html(response: RetailAnalysisResponse) -> HTMLResponse:
        return HTMLResponse(render_report_html(response))

    @router.post("/report/pdf")
    def report_pdf(response: RetailAnalysisResponse) -> Response:
        try:
            payload = render_report_pdf(response)
        except RuntimeError as exc:
            raise HTTPException(503, str(exc)) from exc
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="BA-Agent-{response.task_id}.pdf"'
                )
            },
        )

    @router.post("/benchmark")
    def benchmark() -> dict[str, object]:
        return RetailBenchmarkRunner(retail_agent).run()

    return router
