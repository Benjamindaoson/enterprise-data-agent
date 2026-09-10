from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent import answer, listing_draft, review_insight, stream_events
from app.config import SETTINGS
from app.db import check_db, engine, get_db
from app.models import OperatorUser
from app.observability import error_response, log_request, metrics_text, now_ms, request_id
from app.rate_limit import MemoryRateLimiter, RedisRateLimiter
from app.schemas import AdRequest, ChatRequest, ListingRequest, LoginRequest, RefundRequest, ReviewRequest, SummaryRequest, TrendRequest
from app.security import create_access_token, verify_request_token
from app.telemetry import configure_telemetry
from app.tools import business_trend_chart, high_acos_campaigns, refund_risks, summarize_business


app = FastAPI(title="Crossborder Ops Agent Python")
app.state.settings = SETTINGS
app.state.rate_limiter = MemoryRateLimiter(SETTINGS.rate_limit_per_minute)
app.state.rate_limit_config = SETTINGS.rate_limit_per_minute
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
configure_telemetry(app, engine)


def settings():
    return app.state.settings


def limiter():
    current = settings().rate_limit_per_minute
    if getattr(app.state, "rate_limit_config", None) != current:
        app.state.rate_limiter = build_rate_limiter()
        app.state.rate_limit_config = current
    return app.state.rate_limiter


def build_rate_limiter():
    redis_url = getattr(settings(), "redis_url", "")
    rate_limit = getattr(settings(), "rate_limit_per_minute", 0)
    if redis_url and rate_limit > 0:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return RedisRateLimiter(client, rate_limit)
        except Exception:
            pass
    return MemoryRateLimiter(rate_limit)


def is_public_path(path: str) -> bool:
    return path in {"/actuator/health", "/healthz", "/readyz", "/metrics"} or path.startswith(("/auth", "/docs", "/openapi"))


@app.middleware("http")
async def production_guardrails(request: Request, call_next):
    rid = request.headers.get("x-request-id") or request_id(request)
    request.state.request_id = rid
    start = now_ms()

    if request.method != "OPTIONS":
        key = request.headers.get("sa-token") or request.client.host if request.client else "unknown"
        if not limiter().allow(key):
            return error_response(request, 429, "RATE_LIMITED", "Too many requests")

        if settings().auth_enabled and not is_public_path(request.url.path):
            token = request.headers.get("sa-token") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
            if not token or not verify_request_token(token, settings()):
                return error_response(request, 401, "UNAUTHORIZED", "Missing or invalid token")

    try:
        response = await call_next(request)
    except Exception:
        response = error_response(request, 500, "INTERNAL_ERROR", "Internal server error")
    response.headers["x-request-id"] = rid
    log_request(request.method, request.url.path, response.status_code, rid, now_ms() - start)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed", exc.errors())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code = "UNAUTHORIZED" if exc.status_code == 401 else "REQUEST_ERROR"
    return error_response(request, exc.status_code, code, message)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return error_response(request, 500, "INTERNAL_ERROR", "Internal server error")


@app.get("/actuator/health")
def health():
    try:
        ok = check_db()
    except Exception:
        ok = False
    return {"status": "UP" if ok else "DOWN", "checks": {"database": "UP" if ok else "DOWN"}}


@app.get("/healthz")
def liveness():
    return {"status": "UP"}


@app.get("/readyz")
def readiness():
    return health()


@app.get("/metrics")
def metrics():
    return PlainTextResponse(metrics_text())


@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    if settings().auth_enabled and req.loginCode != getattr(settings(), "login_code", ""):
        raise HTTPException(status_code=401, detail="Invalid login code")
    user = db.scalar(select(OperatorUser).where(OperatorUser.id == req.operatorId))
    if not user:
        raise HTTPException(status_code=400, detail="运营账号不存在")
    token = create_access_token(
        {"operatorId": user.id, "role": user.role, "storeId": user.store_id},
        settings().auth_secret,
        settings().access_token_ttl_seconds,
    )
    return {
        "token": token,
        "username": user.name,
        "role": user.role,
        "operatorId": user.id,
        "storeId": user.store_id or "",
    }


@app.post("/auth/logout")
def logout():
    return {"message": "已退出登录"}


@app.post("/agent/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return {"sessionId": req.sessionId, "content": answer(req.message, db)}


@app.post("/agent/chat/stream")
def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    text = answer(req.message, db)
    return StreamingResponse(stream_events(text), media_type="text/event-stream")


@app.delete("/agent/session/{session_id}")
def clear_session(session_id: str):
    return {"message": "session cleared", "sessionId": session_id}


@app.post("/test/tool/business-summary")
def test_business_summary(req: SummaryRequest | None = None, db: Session = Depends(get_db)):
    req = req or SummaryRequest()
    return summarize_business(db, req.startDate, req.endDate, req.storeName)


@app.post("/test/tool/business-trend-chart")
def test_business_chart(req: TrendRequest | None = None, db: Session = Depends(get_db)):
    req = req or TrendRequest()
    return business_trend_chart(db, req.months, req.storeName, req.title)


@app.post("/test/tool/refund-risks")
def test_refunds(req: RefundRequest | None = None, db: Session = Depends(get_db)):
    req = req or RefundRequest()
    return refund_risks(db, req.startDate, req.endDate, req.storeName, req.topN)


@app.post("/test/tool/high-acos-campaigns")
def test_ads(req: AdRequest | None = None, db: Session = Depends(get_db)):
    req = req or AdRequest()
    return high_acos_campaigns(db, req.startDate, req.endDate, req.storeName, req.thresholdPercent)


@app.post("/test/tool/review-insights")
def test_reviews(req: ReviewRequest | None = None, db: Session = Depends(get_db)):
    return review_insight(db)


@app.post("/test/tool/listing-draft")
def test_listing(req: ListingRequest, db: Session = Depends(get_db)):
    return listing_draft(db, req.skuCode)
