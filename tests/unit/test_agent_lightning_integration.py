from __future__ import annotations

from typing import Any

from eiw.retail.agent_lightning import (
    RetailAgentLightningCase,
    reward_retail_response,
)
from eiw.retail.domain import build_retail_domain_runtime
from eiw.retail.models import RetailAnalysisRequest
from eiw.training.agent_lightning import (
    AgentLightningConfig,
    compose_reward,
    resolve_model_endpoint,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        return None


def test_agent_lightning_env_overrides_model_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("AGL_OPENAI_BASE_URL", "http://agl.test/proxy/openai/v1")
    monkeypatch.setenv("AGL_KEY", "secret")
    monkeypatch.setenv("EIW_AGENT_LIGHTNING_MODEL", "auto")

    url, model, key, source = resolve_model_endpoint(
        "http://direct.test/v1",
        "qwen3",
        "direct-key",
    )

    assert url == "http://agl.test/proxy/openai/v1"
    assert model == "auto"
    assert key == "secret"
    assert source == "agent-lightning"


def test_agent_lightning_posts_reward_event(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    config = AgentLightningConfig(
        openai_base_url="http://agl.test/openai/v1",
        event_url="http://agl.test/events",
        key="secret",
    )
    config.post_reward(0.73, source="test", reason="verified")

    payload = calls[0]["kwargs"]["json"]
    assert payload["event_type"] == "reward"
    assert payload["data"]["value"] == 0.73
    assert calls[0]["kwargs"]["headers"]["Authorization"] == "Bearer secret"


def test_compose_reward_is_bounded_weighted_mean() -> None:
    reward = compose_reward(
        {"quality": 1.2, "safety": 0.5},
        weights={"quality": 3.0, "safety": 1.0},
    )
    assert reward == 0.875


def test_retail_domain_routes_model_policies_through_agent_lightning(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGL_OPENAI_BASE_URL", "http://agl.test/proxy/openai/v1")
    monkeypatch.setenv("AGL_KEY", "secret")
    monkeypatch.setenv("EIW_AGENT_LIGHTNING_MODEL", "auto")
    monkeypatch.delenv("EIW_RETAIL_DATA_DIR", raising=False)

    domain = build_retail_domain_runtime()

    assert domain.agent.planner.policy is not None
    assert domain.agent.planner.policy.base_url == "http://agl.test/proxy/openai/v1"
    assert domain.agent.workers.policy is not None
    assert domain.agent.workers.policy.base_url == "http://agl.test/proxy/openai/v1"


def test_retail_reward_uses_real_response_contract(monkeypatch) -> None:
    monkeypatch.delenv("AGL_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AGL_EVENT_URL", raising=False)
    monkeypatch.delenv("AGL_KEY", raising=False)
    domain = build_retail_domain_runtime()
    response = domain.agent.analyze(
        RetailAnalysisRequest(
            question="Why did recent sales change by store?",
        )
    )
    case = RetailAgentLightningCase(
        case_id="fixture",
        question="Why did recent sales change by store?",
        expected_metrics=["sales_value"],
        expected_dimensions=["store"],
        expected_intents=["diagnose"],
    )
    reward, metrics = reward_retail_response(response, case)

    assert 0.0 <= reward <= 1.0
    assert set(metrics) == {
        "semantic_coverage",
        "driver_recall",
        "action_coverage",
        "task_completion",
    }
