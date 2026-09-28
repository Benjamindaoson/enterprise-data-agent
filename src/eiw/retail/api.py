"""FastAPI router for the retail BA Agent reference vertical."""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.charts import ChartPlanner
from eiw.retail.code_analysis import RetailCodeAnalyst
from eiw.retail.code_worker import (
    DockerCodeSandbox,
    FirstPartyRetailCodeAnalyst,
    OpenAICompatibleCodeGenerator,
)
from eiw.retail.data import RetailDataEngine
from eiw.retail.export import render_report_html, render_report_pdf
from eiw.retail.models import (
    ChartRestyleRequest,
    CodeAnalysisRequest,
    RetailAnalysisRequest,
    RetailAnalysisResponse,
    RuntimeEvent,
)
from eiw.retail.runtime import RetailBARuntime
from eiw.retail.supervisor import OpenAICompatibleSupervisor
from eiw.retail.upstream import (
    DataFormulatorBridge,
    DeepAnalyzeWorker,
    WrenCliAdapter,
    upstream_manifest,
)


def _build_runtime() -> RetailBARuntime:
    configured = os.getenv("EIW_RETAIL_DATA_DIR", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.append(Path("data/retail"))

    data = RetailDataEngine.demo()
    for path in candidates:
        if not path.exists():
            continue
        has_core_data = any(
            (path / name).exists()
            for name in (
                "transactions.parquet",
                "transaction_data.parquet",
                "transactions.csv",
                "transaction_data.csv",
            )
        )
        if has_core_data:
            data = RetailDataEngine.from_complete_journey(path)
            break

    supervisor_url = os.getenv("EIW_RETAIL_SUPERVISOR_URL", "").strip()
    supervisor = None
    if supervisor_url:
        supervisor = OpenAICompatibleSupervisor(
            base_url=supervisor_url,
            model=os.getenv("EIW_RETAIL_SUPERVISOR_MODEL", "qwen3"),
            api_key=os.getenv("EIW_RETAIL_SUPERVISOR_API_KEY", ""),
        )
    return RetailBARuntime(data, supervisor_policy=supervisor)


def create_retail_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/ba/retail", tags=["ba-retail"])
    runtime = _build_runtime()
    history: dict[str, RetailAnalysisResponse] = {}
    history_lock = threading.Lock()

    def remember(response: RetailAnalysisResponse) -> None:
        with history_lock:
            history[response.task_id] = response
            while len(history) > 100:
                history.pop(next(iter(history)))

    def inherit(request: RetailAnalysisRequest) -> RetailAnalysisRequest:
        if not request.parent_task_id:
            return request
        with history_lock:
            parent = history.get(request.parent_task_id)
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
            "dataset": runtime.data.status(),
            "mode": "real-data" if not runtime.data.label.startswith("retail-demo") else "deterministic-demo",
        }

    @router.get("/upstreams")
    def upstreams() -> dict[str, object]:
        repo_root = Path(__file__).resolve().parents[3]
        manifest = upstream_manifest(repo_root)
        df = DataFormulatorBridge(repo_root / "third_party" / "data-formulator")
        deep_url = os.getenv("EIW_DEEPANALYZE_URL", "").strip()
        deep = DeepAnalyzeWorker(base_url=deep_url) if deep_url else None
        code_url = os.getenv("EIW_RETAIL_CODE_MODEL_URL", "").strip()
        sandbox = DockerCodeSandbox()
        wren = WrenCliAdapter()
        return {
            "checked_out": manifest,
            "data_formulator": df.manifest(),
            "first_party_code_worker": {
                "configured": bool(code_url),
                "docker_available": sandbox.available(),
                "model_base_url": code_url or None,
                "model": os.getenv("EIW_RETAIL_CODE_MODEL", "qwen3") if code_url else None,
            },
            "deepanalyze": {
                "configured": bool(deep_url),
                "healthy": deep.health() if deep else False,
                "base_url": deep_url or None,
                "role": "bootstrap fallback",
            },
            "wren": {
                "cli_available": wren.available(),
                "integration_mode": "isolated-cli-or-sidecar",
            },
        }

    @router.post("/analyze")
    def analyze(request: RetailAnalysisRequest) -> dict[str, object]:
        resolved = inherit(request)
        response = runtime.analyze(resolved)
        remember(response)
        return response.model_dump(mode="json")

    @router.get("/runs/{task_id}")
    def get_run(task_id: str) -> dict[str, object]:
        with history_lock:
            response = history.get(task_id)
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
                response = runtime.analyze(resolved, on_event=emit)
                remember(response)
                channel.put({"kind": "result", "payload": response.model_dump(mode="json")})
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
        default_current, default_previous = runtime.data.week_bounds()
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
            analyst = FirstPartyRetailCodeAnalyst(runtime.data, generator, sandbox)
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
            analyst = RetailCodeAnalyst(runtime.data, worker)
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
        return RetailBenchmarkRunner(runtime).run()

    return router
