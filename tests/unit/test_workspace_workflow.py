from datetime import date

import pytest

from eiw.workspace.analysis import AnalysisService
from eiw.workspace.data import IowaData
from eiw.workspace.store import WorkspaceStore


def test_question_resolution_and_unsupported_boundary(tmp_path):
    service = AnalysisService(WorkspaceStore(tmp_path / "state.json"), IowaData(), tmp_path / "artifacts")
    assert service._metric_ids("Compare July 2026 wholesale sales with June 2026 by vendor.") == ["wholesale_sales_amount"]
    assert service._dimension("Compare July 2026 wholesale sales with June 2026 by vendor.") == "vendor"
    assert service._period("Compare July 2026 wholesale sales with June 2026") == (
        date(2026, 7, 1), date(2026, 7, 31), date(2026, 6, 1), date(2026, 6, 30)
    )
    assert service._metric_ids("Why did store profit fall?") == []


def test_store_round_trip(tmp_path):
    store = WorkspaceStore(tmp_path / "state.json")
    store.put_task({"task_id": "task-1", "state": "CREATED"})
    store.add_event("task-1", "TASK_CREATED", "created")
    reopened = WorkspaceStore(tmp_path / "state.json")
    assert reopened.get_task("task-1")["state"] == "CREATED"
    assert reopened.events("task-1")[0]["message"] == "created"


@pytest.mark.skipif(not IowaData().available(), reason="official curated snapshot is not present")
def test_real_snapshot_supports_metric_query():
    data = IowaData()
    rows = data.aggregate(date(2026, 7, 1), date(2026, 7, 31), ["wholesale_sales_amount"])
    assert rows and rows[0]["wholesale_sales_amount"] is not None
