"""FastAPI router for the retail BA Agent reference vertical."""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.charts import ChartPlanner
from eiw.retail.code_analysis import RetailCodeAnalyst
from eiw.retail.data import RetailDataEngine
from eiw.retail.export import render_report_html
from eiw.retail.models import (
    ChartRestyleRequest,
    CodeAnalysisRequest,
    RetailAnalysisRequest,
    RetailAnalysisResponse,
    RuntimeEvent,
)
from eiw.retail.runtime import RetailBARuntime
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
            return RetailBARuntime(RetailDataEngine.from_complete_journey(path))
    return RetailBARuntime(RetailDataEngine.demo())


def create_retail_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/ba/retail", tags=["ba-retail"])
    runtime = _build_runtime()

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
        wren = WrenCliAdapter()
        return {
            "checked_out": manifest,
            "data_formulator": df.manifest(),
            "deepanalyze": {
                "configured": bool(deep_url),
                "healthy": deep.health() if deep else False,
                "base_url": deep_url or None,
            },
            "wren": {
                "cli_available": wren.available(),
                "integration_mode": "isolated-cli-or-sidecar",
            },
        }

    @router.post("/analyze")
    def analyze(request: RetailAnalysisRequest) -> dict[str, object]:
        return runtime.analyze(request).model_dump(mode="json")

    @router.post("/analyze/stream")
    def analyze_stream(request: RetailAnalysisRequest) -> StreamingResponse:
        channel: queue.Queue[dict[str, object] | None] = queue.Queue()

        def emit(event: RuntimeEvent) -> None:
            channel.put({"kind": "event", "payload": event.model_dump(mode="json")})

        def run() -> None:
            try:
                response = runtime.analyze(request, on_event=emit)
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
        base_url = os.getenv("EIW_DEEPANALYZE_URL", "").strip()
        if not base_url:
            raise HTTPException(
                status_code=503,
                detail="EIW_DEEPANALYZE_URL is not configured",
            )
        worker = DeepAnalyzeWorker(base_url=base_url)
        if not worker.health():
            raise HTTPException(status_code=503, detail="DeepAnalyze API is unavailable")
        default_current, default_previous = runtime.data.week_bounds()
        analyst = RetailCodeAnalyst(runtime.data, worker)
        return analyst.analyze(
            request.instruction,
            current_weeks=request.current_weeks or default_current,
            previous_weeks=request.previous_weeks or default_previous,
            max_rows=request.max_rows,
        )

    @router.post("/charts/restyle")
    def restyle_chart(request: ChartRestyleRequest) -> dict[str, object]:
        chart = ChartPlanner().restyle(request.chart, request.instruction)
        return chart.model_dump(mode="json")

    @router.post("/report/html", response_class=HTMLResponse)
    def report_html(response: RetailAnalysisResponse) -> HTMLResponse:
        return HTMLResponse(render_report_html(response))

    @router.post("/benchmark")
    def benchmark() -> dict[str, object]:
        return RetailBenchmarkRunner(runtime).run()

    return router
