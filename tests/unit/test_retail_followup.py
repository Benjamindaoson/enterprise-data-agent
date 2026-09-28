from __future__ import annotations

from fastapi.testclient import TestClient

from eiw.app import create_app
from eiw.retail.data import RetailDataEngine
from eiw.retail.models import RetailAnalysisRequest
from eiw.retail.runtime import RetailBARuntime


def test_focus_drilldown_returns_scoped_driver_and_chart() -> None:
    runtime = RetailBARuntime(RetailDataEngine.demo())
    response = runtime.analyze(
        RetailAnalysisRequest(
            question="Continue into store 3 and explain the main category driver.",
            parent_task_id="parent-1",
            focus={"store": "3"},
            top_k=5,
        )
    )

    assert response.parent_task_id == "parent-1"
    assert response.insights
    assert response.insights[0].kind == "focus_drilldown"
    assert response.insights[0].dimensions["store"] == "3"
    assert "commodity" in response.insights[0].dimensions
    assert response.charts
    assert response.charts[0].title.startswith("Focused drill-down")


def test_api_followup_inherits_parent_period_window() -> None:
    client = TestClient(create_app())

    first = client.post(
        "/api/v1/ba/retail/analyze",
        json={"question": "Analyze recent sales performance and key drivers."},
    )
    assert first.status_code == 200
    parent = first.json()

    follow = client.post(
        "/api/v1/ba/retail/analyze",
        json={
            "question": "Continue into this store and explain the category drivers.",
            "parent_task_id": parent["task_id"],
            "focus": {"store": "3"},
        },
    )
    assert follow.status_code == 200
    child = follow.json()

    assert child["parent_task_id"] == parent["task_id"]
    assert child["current_weeks"] == parent["current_weeks"]
    assert child["previous_weeks"] == parent["previous_weeks"]
    assert child["insights"][0]["kind"] == "focus_drilldown"

    stored = client.get(f"/api/v1/ba/retail/runs/{child['task_id']}")
    assert stored.status_code == 200
    assert stored.json()["task_id"] == child["task_id"]
