from __future__ import annotations

import time
from collections import defaultdict, deque


class MemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = max(0, limit)
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        now = now if now is not None else time.time()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


class RedisRateLimiter:
    def __init__(self, redis_client, limit: int, window_seconds: int = 60):
        self.redis = redis_client
        self.limit = max(0, limit)
        self.window_seconds = window_seconds

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        bucket = int((now if now is not None else time.time()) // self.window_seconds)
        redis_key = f"rate:{bucket}:{key}"
        count = self.redis.incr(redis_key)
        if count == 1:
            self.redis.expire(redis_key, self.window_seconds + 5)
        return count <= self.limit
