"""FastAPI router for the retail BA Agent reference vertical."""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from eiw.retail.benchmark import RetailBenchmarkRunner
from eiw.retail.data import RetailDataEngine
from eiw.retail.charts import ChartPlanner
from eiw.retail.models import ChartRestyleRequest, RetailAnalysisRequest, RuntimeEvent
from eiw.retail.runtime import RetailBARuntime


def _build_runtime() -> RetailBARuntime:
    configured = os.getenv("EIW_RETAIL_DATA_DIR", "").strip()
    if configured:
        path = Path(configured)
        if path.exists():
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

    @router.post("/charts/restyle")
    def restyle_chart(request: ChartRestyleRequest) -> dict[str, object]:
        chart = ChartPlanner().restyle(request.chart, request.instruction)
        return chart.model_dump(mode="json")

    @router.post("/benchmark")
    def benchmark() -> dict[str, object]:
        return RetailBenchmarkRunner(runtime).run()

    return router
