import asyncio

from eiw.production.canary import RegressionGate
from eiw.production.costing import CostLedger, ModelPrice
from eiw.production.queue import AsyncTaskQueue, TaskEnvelope
from eiw.production.routing import ModelTier, ModelRouter
from eiw.production.worker import AsyncAgentWorker


def test_model_router_uses_risk_complexity_and_budget():
    router = ModelRouter()
    assert router.route(complexity=0.1, risk=0.1, remaining_tokens=5000).tier == ModelTier.FAST
    assert router.route(complexity=0.5, risk=0.2, remaining_tokens=5000).tier == ModelTier.STANDARD
    assert router.route(complexity=0.4, risk=0.9, remaining_tokens=5000).tier == ModelTier.REASONING
    assert router.route(complexity=0.9, risk=0.9, remaining_tokens=800).tier == ModelTier.FAST


def test_cost_ledger_requires_explicit_price_configuration():
    ledger = CostLedger({"model-a": ModelPrice(1.0, 2.0)})
    cost = ledger.record("model-a", input_tokens=1_000_000, output_tokens=500_000)
    assert cost == 2.0
    assert ledger.snapshot()["calls"] == 1


def test_regression_gate_blocks_safety_regression():
    baseline = {
        "success_rate": 0.80,
        "policy_violation_rate": 0.01,
        "invalid_action_rate": 0.10,
        "average_cost": 1.0,
    }
    candidate = {
        "success_rate": 0.82,
        "policy_violation_rate": 0.08,
        "invalid_action_rate": 0.08,
        "average_cost": 1.1,
    }
    result = RegressionGate().compare(baseline, candidate)
    assert result["passed"] is False
    assert "policy_violation_rate regression" in result["reasons"]


def test_async_worker_requeues_failed_task():
    async def run() -> None:
        queue = AsyncTaskQueue()
        await queue.put(TaskEnvelope("t1", "analysis", {"x": 1}))
        attempts = 0

        async def handler(task: TaskEnvelope) -> dict[str, object]:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("transient")
            return {"task_id": task.task_id, "status": "OK"}

        worker = AsyncAgentWorker(queue, handler)
        first = await worker.run_once()
        second = await worker.run_once()
        assert first["status"] == "RETRY_SCHEDULED"
        assert second["status"] == "OK"

    asyncio.run(run())
