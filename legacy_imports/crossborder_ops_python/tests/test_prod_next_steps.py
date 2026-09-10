import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.agent as agent
from app.observability import AGENT_EVENT_COUNTS, metrics_text
from app.eval_runner import run_eval_cases
from app.rate_limit import RedisRateLimiter
from app.security import verify_request_token
from app.seed import init_db, seed_demo_data
from app.telemetry import configure_telemetry


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds


def test_redis_rate_limiter_blocks_after_limit():
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, limit=2, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is False
    assert redis.expirations


def test_eval_runner_scores_static_cases(tmp_path):
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        "\n".join([
            json.dumps({"question": "show trend chart", "mustContain": ["VISUAL_PAYLOAD:"]}),
            json.dumps({"question": "refund risk", "mustContain": ["YM-US-2001"]}),
        ]),
        encoding="utf-8",
    )

    result = run_eval_cases(cases)

    assert result["passed"] == 2
    assert result["failed"] == 0


def test_telemetry_configure_is_safe_without_collector(monkeypatch):
    monkeypatch.setenv("OTEL_ENABLED", "false")

    assert configure_telemetry(None, None) is False


def test_agent_tool_events_are_exposed_in_metrics():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = sessionmaker(engine)
    db = Session()
    seed_demo_data(db)
    AGENT_EVENT_COUNTS.clear()

    text = agent.route_tool("show trend chart", db)

    assert text.startswith("VISUAL_PAYLOAD:")
    assert "crossborder_agent_events_total" in metrics_text()
    assert AGENT_EVENT_COUNTS["tool_success"] == 1


def test_oidc_mode_rejects_when_provider_configuration_is_missing():
    class Settings:
        identity_provider = "oidc"
        oidc_jwks_url = ""
        oidc_audience = ""
        oidc_issuer = ""
        auth_secret = "local-secret"

    assert verify_request_token("token", Settings()) is None


def test_alembic_initial_migration_runs_against_sqlite(tmp_path):
    db_path = tmp_path / "migration.db"
    env = os.environ.copy()
    env["DB_URL"] = f"sqlite:///{db_path.as_posix()}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()
