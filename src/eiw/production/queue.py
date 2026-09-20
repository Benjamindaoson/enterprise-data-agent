"""Async in-process and Redis-backed task queues."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TaskEnvelope:
    task_id: str
    task_type: str
    payload: dict[str, Any]
    attempt: int = 0


class AsyncTaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[TaskEnvelope] = asyncio.Queue()

    async def put(self, task: TaskEnvelope) -> None:
        await self._queue.put(task)

    async def get(self) -> TaskEnvelope:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()


class RedisTaskQueue:
    def __init__(self, redis_url: str, *, key: str = "eiw:tasks") -> None:
        try:
            from redis.asyncio import Redis
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("install production extras: pip install -e '.[production]'") from exc
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.key = key

    async def put(self, task: TaskEnvelope) -> None:
        await self.redis.lpush(self.key, json.dumps(asdict(task), sort_keys=True))

    async def get(self, timeout: int = 5) -> TaskEnvelope:
        result = await self.redis.brpop(self.key, timeout=timeout)
        if result is None:
            raise TimeoutError("redis task queue timed out")
        _, payload = result
        return TaskEnvelope(**json.loads(payload))

    async def close(self) -> None:
        await self.redis.aclose()
