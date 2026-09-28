from __future__ import annotations

from typing import Any

from eiw.retail.data import RetailDataEngine
from eiw.retail.model_lane_benchmark import RetailModelLaneBenchmark
from eiw.retail.models import WorkstreamName
from eiw.retail.single_agent_policy import OpenAICompatibleSingleAgentPolicy


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"workstreams":["store","product"],'
                            '"skills":{"store":["store_contribution","bad_tool"],'
                            '"product":["commodity_contribution"]},'
                            '"rationale":"inspect bounded drivers"}'
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        }


def test_single_agent_policy_uses_one_cached_model_plan(monkeypatch) -> None:
    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())
    policy = OpenAICompatibleSingleAgentPolicy(
        base_url="http://model.test/v1",
        model="fixture",
    )

    supervisor = policy.decide(
        stage="initial",
        question="Why did sales change?",
        completed=[],
        max_workstreams=5,
    )
    specialist = policy.decide(
        workstream=WorkstreamName.STORE,
        question="Why did sales change?",
        allowed_skills=("store_contribution", "store_anomaly"),
    )

    assert [item.value for item in supervisor.workstreams] == ["store", "product"]
    assert specialist.skills == ["store_contribution"]
    assert policy.telemetry.calls == 1
    assert policy.telemetry.invalid_choices == 1
    assert policy.telemetry.total_tokens == 120


def test_model_lane_benchmark_always_emits_deterministic_reference() -> None:
    result = RetailModelLaneBenchmark(RetailDataEngine.demo()).run([])

    assert result["live_model_results"] is False
    assert result["providers"] == []
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["lane"] == "deterministic"
    assert row["cost_usd"] == 0.0
    assert 0.0 <= row["success"] <= 1.0
