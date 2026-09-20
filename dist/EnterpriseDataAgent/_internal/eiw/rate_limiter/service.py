"""Rate Limiter Service.

Provides Redis-based rate limiting for API endpoints and task execution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis.asyncio as redis

from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "rate_limiter")


class RateLimitScope(str, Enum):
    """Rate limit scope types."""

    USER = "user"  # Per-user limit
    TEAM = "team"  # Per-team limit
    GLOBAL = "global"  # System-wide limit
    ENDPOINT = "endpoint"  # Per-endpoint limit


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit."""

    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_size: int = 10  # Allow short bursts


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining_minute: int
    remaining_hour: int
    remaining_day: int
    reset_at: float
    scope: RateLimitScope
    identifier: str


# Default limits
DEFAULT_USER_LIMITS = RateLimitConfig(
    requests_per_minute=30,
    requests_per_hour=500,
    requests_per_day=5000,
    burst_size=10,
)

DEFAULT_TEAM_LIMITS = RateLimitConfig(
    requests_per_minute=100,
    requests_per_hour=2000,
    requests_per_day=20000,
    burst_size=20,
)

DEFAULT_GLOBAL_LIMITS = RateLimitConfig(
    requests_per_minute=1000,
    requests_per_hour=20000,
    requests_per_day=100000,
    burst_size=50,
)

DEFAULT_ENDPOINT_LIMITS = RateLimitConfig(
    requests_per_minute=60,
    requests_per_hour=2000,
    requests_per_day=20000,
    burst_size=15,
)


class RateLimiter:
    """Redis-based distributed rate limiter."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_config: RateLimitConfig | None = None,
    ):
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self._default_config = default_config or DEFAULT_USER_LIMITS

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_key(self, scope: RateLimitScope, identifier: str, window: str) -> str:
        """Generate Redis key for rate limit."""
        return f"rate_limit:{scope.value}:{identifier}:{window}"

    async def check_rate_limit(
        self,
        identifier: str,
        scope: RateLimitScope = RateLimitScope.USER,
        config: RateLimitConfig | None = None,
    ) -> RateLimitResult:
        """Check if request is within rate limits.

        Args:
            identifier: Unique identifier (user_id, team_id, etc.)
            scope: Rate limit scope
            config: Override default limits

        Returns:
            Rate limit result with remaining quotas
        """
        config = config or self._default_config
        r = await self._get_redis()
        now = time.time()

        # Check minute window
        minute_key = self._get_key(scope, identifier, "minute")
        minute_count = await r.get(minute_key)
        minute_remaining = config.requests_per_minute - (int(minute_count) if minute_count else 0)

        # Check hour window
        hour_key = self._get_key(scope, identifier, "hour")
        hour_count = await r.get(hour_key)
        hour_remaining = config.requests_per_hour - (int(hour_count) if hour_count else 0)

        # Check day window
        day_key = self._get_key(scope, identifier, "day")
        day_count = await r.get(day_key)
        day_remaining = config.requests_per_day - (int(day_count) if day_count else 0)

        # Determine if allowed
        allowed = (
            minute_remaining > 0
            and hour_remaining > 0
            and day_remaining > 0
        )

        if allowed:
            # Increment counters
            pipe = r.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)
            await pipe.execute()

            # Recalculate remaining
            minute_remaining -= 1
            hour_remaining -= 1
            day_remaining -= 1

        # Calculate reset time
        reset_at = now + 60  # Minute window resets soonest

        return RateLimitResult(
            allowed=allowed,
            remaining_minute=max(0, minute_remaining),
            remaining_hour=max(0, hour_remaining),
            remaining_day=max(0, day_remaining),
            reset_at=reset_at,
            scope=scope,
            identifier=identifier,
        )

    async def get_usage(
        self,
        identifier: str,
        scope: RateLimitScope = RateLimitScope.USER,
    ) -> dict[str, int]:
        """Get current usage for an identifier."""
        r = await self._get_redis()

        minute_key = self._get_key(scope, identifier, "minute")
        hour_key = self._get_key(scope, identifier, "hour")
        day_key = self._get_key(scope, identifier, "day")

        pipe = r.pipeline()
        pipe.get(minute_key)
        pipe.get(hour_key)
        pipe.get(day_key)
        results = await pipe.execute()

        return {
            "minute": int(results[0]) if results[0] else 0,
            "hour": int(results[1]) if results[1] else 0,
            "day": int(results[2]) if results[2] else 0,
        }

    async def reset_limit(
        self,
        identifier: str,
        scope: RateLimitScope = RateLimitScope.USER,
    ) -> None:
        """Reset rate limits for an identifier."""
        r = await self._get_redis()

        keys = [
            self._get_key(scope, identifier, "minute"),
            self._get_key(scope, identifier, "hour"),
            self._get_key(scope, identifier, "day"),
        ]
        await r.delete(*keys)

        logger.info(f"Reset rate limits for {scope.value}:{identifier}")


# Global rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _rate_limiter = RateLimiter(redis_url)
    return _rate_limiter
