"""Rate Limiter Middleware for FastAPI.

Provides rate limiting for API endpoints.
"""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from eiw.rate_limiter import (
    RateLimitScope,
    RateLimitResult,
    get_rate_limiter,
)
from eiw.observability.logging import get_structured_logger

logger = get_structured_logger(__name__, "rate_limiter_middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    # Paths to skip rate limiting
    SKIP_PATHS = {
        "/api/v1/health",
        "/api/v1/billing/status",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/static",
    }

    def __init__(
        self,
        app: Any,
        default_scope: RateLimitScope = RateLimitScope.USER,
    ):
        super().__init__(app)
        self._default_scope = default_scope
        self._rate_limiter = get_rate_limiter()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for certain paths
        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        # Determine identifier and scope
        identifier, scope = self._get_identifier(request)

        # Check rate limit
        try:
            result = await self._rate_limiter.check_rate_limit(
                identifier=identifier,
                scope=scope,
            )
        except Exception as e:
            # If Redis is unavailable, allow request but log warning
            logger.warning(f"Rate limiter unavailable: {e}")
            return await call_next(request)

        # Add rate limit headers
        headers = {
            "X-RateLimit-Remaining-Minute": str(result.remaining_minute),
            "X-RateLimit-Remaining-Hour": str(result.remaining_hour),
            "X-RateLimit-Remaining-Day": str(result.remaining_day),
            "X-RateLimit-Reset": str(int(result.reset_at)),
        }

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for {scope.value}:{identifier}",
                extra={"path": path},
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": int(result.reset_at - __import__("time").time()),
                },
                headers={
                    "Retry-After": str(int(result.reset_at - __import__("time").time())),
                    **headers,
                },
            )

        # Process request
        response = await call_next(request)

        # Add headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    def _get_identifier(self, request: Request) -> tuple[str, RateLimitScope]:
        """Get identifier and scope from request.

        Args:
            request: FastAPI request

        Returns:
            Tuple of (identifier, scope)
        """
        # Try to get user from auth header or token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # In production, decode JWT to get user_id
            # For now, use token hash as identifier
            import hashlib
            identifier = hashlib.sha256(token.encode()).hexdigest()[:16]
            return identifier, RateLimitScope.USER

        # Fall back to IP-based limiting
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}", RateLimitScope.GLOBAL


async def check_rate_limit(
    identifier: str,
    scope: RateLimitScope = RateLimitScope.USER,
) -> RateLimitResult:
    """Convenience function to check rate limit.

    Args:
        identifier: User/team identifier
        scope: Rate limit scope

    Returns:
        Rate limit result
    """
    limiter = get_rate_limiter()
    return await limiter.check_rate_limit(identifier, scope)
