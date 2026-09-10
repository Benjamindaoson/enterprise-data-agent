import time

from fastapi.testclient import TestClient

import app.main as main
from app.db import get_db


class DummySettings:
    app_name = "test"
    environment = "test"
    auth_enabled = False
    auth_secret = "test-secret"
    cors_origins = ["*"]
    rate_limit_per_minute = 0
    llm_enabled = False


def client_with(settings=None):
    main.app.state.settings = settings or DummySettings()
    return TestClient(main.app)


def test_health_returns_down_when_database_raises(monkeypatch):
    monkeypatch.setattr(main, "check_db", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    res = client_with().get("/actuator/health")

    assert res.status_code == 200
    assert res.json()["status"] == "DOWN"
    assert res.headers["x-request-id"]


def test_validation_error_uses_structured_payload():
    res = client_with().post("/agent/chat", json={"sessionId": "s1"})

    assert res.status_code == 422
    body = res.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["requestId"]
    assert "message" in body


def test_auth_enabled_rejects_missing_token(monkeypatch):
    settings = DummySettings()
    settings.auth_enabled = True
    main.app.dependency_overrides[get_db] = lambda: None
    try:
        res = client_with(settings).post("/agent/chat", json={"sessionId": "s1", "message": "summary"})
    finally:
        main.app.dependency_overrides.clear()

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_auth_enabled_login_requires_login_code():
    settings = DummySettings()
    settings.auth_enabled = True
    settings.login_code = "let-me-in"

    res = client_with(settings).post("/auth/login", json={"operatorId": 3})

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHORIZED"


def test_auth_enabled_accepts_valid_token(monkeypatch):
    from app.security import create_access_token

    settings = DummySettings()
    settings.auth_enabled = True
    token = create_access_token({"operatorId": 7}, settings.auth_secret, ttl_seconds=60)
    monkeypatch.setattr(main, "answer", lambda message, db: "ok")
    main.app.dependency_overrides[get_db] = lambda: None
    try:
        res = client_with(settings).post(
            "/agent/chat",
            json={"sessionId": "s1", "message": "summary"},
            headers={"sa-token": token},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert res.status_code == 200
    assert res.json()["content"] == "ok"


def test_hmac_token_round_trip_and_tamper_rejection():
    from app.security import create_access_token, verify_access_token

    token = create_access_token({"operatorId": 7, "role": "OPERATOR"}, "secret", ttl_seconds=60)

    assert verify_access_token(token, "secret")["operatorId"] == 7
    assert verify_access_token(token + "x", "secret") is None


def test_memory_rate_limiter_blocks_excess_requests():
    from app.rate_limit import MemoryRateLimiter

    limiter = MemoryRateLimiter(limit=2, window_seconds=60)
    now = time.time()

    assert limiter.allow("ip:1", now) is True
    assert limiter.allow("ip:1", now + 1) is True
    assert limiter.allow("ip:1", now + 2) is False
    assert limiter.allow("ip:1", now + 61) is True


def test_unhandled_endpoint_error_is_structured(monkeypatch):
    monkeypatch.setattr(main, "answer", lambda message, db: (_ for _ in ()).throw(RuntimeError("boom")))

    res = client_with().post("/agent/chat", json={"sessionId": "s1", "message": "summary"})

    assert res.status_code == 500
    assert res.json()["code"] == "INTERNAL_ERROR"
    assert res.json()["requestId"]


def test_metrics_endpoint_exposes_request_counter():
    client = client_with()
    client.get("/healthz")

    res = client.get("/metrics")

    assert res.status_code == 200
    assert "crossborder_http_requests_total" in res.text
