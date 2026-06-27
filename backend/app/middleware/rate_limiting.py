"""
Simple Redis-based rate limiting middleware.

Limits requests per IP address (or authenticated user) within a sliding window.
Configurable via the constructor:
    - max_requests: max requests allowed in the window
    - window_seconds: sliding window duration
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("nutrimed.ratelimit")

# Paths that are exempt from rate limiting
_EXEMPT_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding-window rate limiter."""

    def __init__(
        self,
        app,
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for exempt paths
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Determine key: prefer user_id from JWT, fall back to IP
        key_id = self._get_key(request)
        redis_key = f"ratelimit:{key_id}"

        try:
            from app.core.database import get_redis

            redis = get_redis()

            # Increment counter
            current = await redis.incr(redis_key)
            if current == 1:
                # First request in window -- set expiry
                await redis.expire(redis_key, self.window_seconds)

            ttl = await redis.ttl(redis_key)

            if current > self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again later.",
                        "retry_after_seconds": ttl if ttl > 0 else self.window_seconds,
                    },
                    headers={
                        "Retry-After": str(ttl if ttl > 0 else self.window_seconds),
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ttl if ttl > 0 else self.window_seconds),
                    },
                )

            response = await call_next(request)
            remaining = max(0, self.max_requests - current)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(ttl if ttl > 0 else self.window_seconds)
            return response

        except Exception as exc:
            # If Redis is unavailable, allow the request through (fail open)
            logger.warning("Rate limiter unavailable (Redis error): %s", exc)
            return await call_next(request)

    @staticmethod
    def _get_key(request: Request) -> str:
        """Extract a unique key for rate limiting."""
        # Try to get user_id from JWT
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
            try:
                from app.core.security import verify_access_token

                payload = verify_access_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                pass

        # Fall back to IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
