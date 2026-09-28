from __future__ import annotations

from typing import Any

import pytest

from eiw.runtime.orchestrator import BusinessAgentRuntime


class FakeDomain:
    domain_id = "fake"

    def __init__(self) -> None:
        self.calls: list[object] = []

    def capabilities(self) -> dict[str, Any]:
        return {"kind": "fake"}

    def analyze(self, request: object, *, on_event=None) -> dict[str, object]:
        self.calls.append(request)
        if on_event is not None:
            on_event({"event_type": "fake"})
        return {"task_id": "fake-1", "status": "COMPLETED", "request": request}


def test_business_runtime_hosts_domain_runtime() -> None:
    domain = FakeDomain()
    runtime = BusinessAgentRuntime(analysis_service=None, domains=[domain])

    emitted: list[object] = []
    result = runtime.analyze_domain(
        "fake",
        {"question": "hello"},
        on_event=emitted.append,
    )

    assert result["task_id"] == "fake-1"
    assert domain.calls == [{"question": "hello"}]
    assert emitted == [{"event_type": "fake"}]
    assert runtime.capabilities()["domains"]["fake"]["kind"] == "fake"

    events = runtime.events()
    event_types = [event["event_type"] for event in events]
    assert "DOMAIN_RUNTIME_STARTED" in event_types
    assert "DOMAIN_RUNTIME_COMPLETED" in event_types


def test_domain_registration_is_unique_and_generic_analysis_requires_service() -> None:
    runtime = BusinessAgentRuntime(analysis_service=None)
    runtime.register_domain(FakeDomain())

    with pytest.raises(ValueError, match="already registered"):
        runtime.register_domain(FakeDomain())

    with pytest.raises(RuntimeError, match="analysis service"):
        runtime.analyze("question", {})
