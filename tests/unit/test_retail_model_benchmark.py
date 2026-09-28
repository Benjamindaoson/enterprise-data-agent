from __future__ import annotations

import json

from eiw.retail.data import RetailDataEngine
from eiw.retail.model_benchmark import ModelArchitectureBenchmark
from eiw.retail.model_client import ChatResult, PolicyTelemetry, UsageLedger
from eiw.retail.supervisor import OpenAICompatibleSupervisor


class FakeChatClient:
    def __init__(self, *, inject_invalid: bool = False) -> None:
        self.ledger = UsageLedger()
        self.inject_invalid = inject_invalid

    def complete(self, *, system: str, user: str) -> ChatResult:
        payload = json.loads(user)
        if "allowed_workstreams" in payload:
            workstreams = list(payload["allowed_workstreams"])
            if self.inject_invalid:
                workstreams.append("root_shell")
            content = json.dumps(
                {
                    "workstreams": workstreams,
                    "rationale": "bounded fake supervisor decision",
                }
            )
        else:
            content = json.dumps(
                {
                    "skills": list(payload["allowed_skills"]),
                    "rationale": "bounded fake specialist decision",
                }
            )
        result = ChatResult(
            content=content,
            prompt_tokens=20,
            completion_tokens=10,
            cost_usd=0.001,
            latency_ms=2.0,
        )
        self.ledger.add(result)
        return result


def test_model_architecture_benchmark_tracks_calls_cost_and_modes() -> None:
    result = ModelArchitectureBenchmark(
        RetailDataEngine.demo(),
        provider="fake",
        model="fake-model",
        client_factory=FakeChatClient,
    ).run(case_limit=2)

    rows = result["architectures"]
    assert isinstance(rows, list)
    assert [row["architecture"] for row in rows] == [
        "deterministic",
        "single-agent",
        "supervisor",
        "supervisor+specialists",
    ]
    assert rows[0]["model_calls"] == 0
    assert all(row["model_calls"] > 0 for row in rows[1:])
    assert all(row["cost_usd"] > 0 for row in rows[1:])


def test_supervisor_filters_and_counts_invalid_workstream() -> None:
    telemetry = PolicyTelemetry()
    supervisor = OpenAICompatibleSupervisor(
        base_url="instrumented://fake",
        model="fake",
        client=FakeChatClient(inject_invalid=True),
        telemetry=telemetry,
    )

    decision = supervisor.decide(
        stage="initial",
        question="Analyze recent sales.",
        completed=[],
        max_workstreams=5,
    )

    assert all(item.value != "root_shell" for item in decision.workstreams)
    snapshot = telemetry.snapshot()
    assert snapshot["invalid_items"] == 1
    assert snapshot["invalid_decision_rate"] == 1.0
