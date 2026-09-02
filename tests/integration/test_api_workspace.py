import pytest
from fastapi.testclient import TestClient

from eiw.app import app
from eiw.workspace.data import IowaData


@pytest.mark.skipif(not IowaData().available(), reason="official curated snapshot is not present")
def test_task_workspace_follow_up_and_artifact_flow():
    client = TestClient(app)
    created = client.post("/api/v1/analysis-tasks", json={"question": "Compare July 2026 wholesale sales with June 2026 by vendor."})
    assert created.status_code == 200
    task = created.json()
    assert task["state"] == "COMPLETED"
    assert task["claims"] and task["evidence"]
    assert client.get(f"/api/v1/analysis-tasks/{task['task_id']}/events").status_code == 200
    report = client.get(f"/api/v1/analysis-tasks/{task['task_id']}/artifacts/report.md")
    assert report.status_code == 200
    assert "Executive Summary" in report.text
    child = client.post(f"/api/v1/analysis-tasks/{task['task_id']}/follow-ups", json={"question": "Why did the top vendor change?"})
    assert child.status_code == 200
    assert child.json()["lineage"]["parent_task_id"] == task["task_id"]
