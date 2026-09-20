"""Asynchronous task worker with checkpoint and retry hooks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from eiw.production.queue import TaskEnvelope


class QueueProtocol(Protocol):
    async def get(self) -> TaskEnvelope: ...


Handler = Callable[[TaskEnvelope], Awaitable[dict[str, object]]]


class AsyncAgentWorker:
    def __init__(
        self,
        queue: QueueProtocol,
        handler: Handler,
        *,
        max_attempts: int = 3,
    ) -> None:
        self.queue = queue
        self.handler = handler
        self.max_attempts = max_attempts

    async def run_once(self) -> dict[str, object]:
        task = await self.queue.get()
        try:
            return await self.handler(task)
        except Exception:
            if task.attempt + 1 >= self.max_attempts:
                raise
            retry = TaskEnvelope(
                task_id=task.task_id,
                task_type=task.task_type,
                payload=task.payload,
                attempt=task.attempt + 1,
            )
            put = getattr(self.queue, "put", None)
            if put is not None:
                await put(retry)
            return {"task_id": task.task_id, "status": "RETRY_SCHEDULED", "attempt": retry.attempt}


async def run_worker_forever(worker: AsyncAgentWorker, *, idle_sleep: float = 0.05) -> None:
    while True:
        try:
            await worker.run_once()
        except TimeoutError:
            await asyncio.sleep(idle_sleep)
