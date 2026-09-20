import asyncio
import os

import pytest

from eiw.production.persistence import ProductionStore
from eiw.production.queue import RedisTaskQueue, TaskEnvelope


@pytest.mark.integration
def test_postgres_trajectory_checkpoint_and_approval_round_trip():
    database_url = os.getenv("EIW_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("EIW_TEST_DATABASE_URL not configured")
    store = ProductionStore(database_url)
    task_id = "integration-task"
    trajectory_id = "integration-trajectory"
    store.purge_task(task_id)

    store.append_trajectory_event(
        trajectory_id=trajectory_id,
        task_id=task_id,
        step_index=0,
        payload={"action": "inspect_metric"},
    )
    store.append_trajectory_event(
        trajectory_id=trajectory_id,
        task_id=task_id,
        step_index=1,
        payload={"action": "cross_check"},
    )
    assert [row["step_index"] for row in store.load_trajectory(trajectory_id)] == [0, 1]

    store.save_checkpoint(task_id=task_id, version=1, payload={"step": 2})
    checkpoint = store.load_checkpoint(task_id)
    assert checkpoint is not None
    assert checkpoint["version"] == 1
    assert checkpoint["payload"]["step"] == 2

    approval_id = store.request_approval(
        task_id=task_id,
        action_id="campaign-write",
        requested_by="agent",
    )
    store.decide_approval(approval_id, approved=True, decided_by="human-reviewer")
    approval = store.get_approval(approval_id)
    assert approval is not None
    assert approval["status"] == "APPROVED"


@pytest.mark.integration
def test_redis_queue_round_trip():
    redis_url = os.getenv("EIW_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("EIW_TEST_REDIS_URL not configured")

    async def run() -> None:
        queue = RedisTaskQueue(redis_url, key="eiw:test:tasks")
        await queue.redis.delete(queue.key)
        await queue.put(TaskEnvelope("t1", "analysis", {"question": "why"}))
        item = await queue.get(timeout=2)
        assert item.task_id == "t1"
        assert item.payload["question"] == "why"
        await queue.close()

    asyncio.run(run())
