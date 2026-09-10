from __future__ import annotations

import json
import logging
import time
import uuid
from collections import Counter

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("crossborder_ops")
REQUEST_COUNTS: Counter[str] = Counter()
AGENT_EVENT_COUNTS: Counter[str] = Counter()


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "") or request.headers.get("x-request-id") or str(uuid.uuid4())


def error_response(request: Request, status_code: int, code: str, message: str, details=None) -> JSONResponse:
    rid = request_id(request)
    payload = {"requestId": rid, "code": code, "message": message}
    if details:
        payload["details"] = details
    return JSONResponse(payload, status_code=status_code, headers={"x-request-id": rid})


def log_request(method: str, path: str, status_code: int, rid: str, elapsed_ms: float) -> None:
    REQUEST_COUNTS[f"{method} {path} {status_code}"] += 1
    logger.info(json.dumps({"event": "http_request", "method": method, "path": path, "status": status_code, "requestId": rid, "elapsedMs": round(elapsed_ms, 2)}, ensure_ascii=False))


def log_agent_event(event: str, **fields) -> None:
    AGENT_EVENT_COUNTS[event] += 1
    logger.info(json.dumps({"event": event, **fields}, ensure_ascii=False))


def now_ms() -> float:
    return time.perf_counter() * 1000
