"""Redis-backed sliding window rate limiting middleware.
Protects API from burst abuse with graceful soft failure if cache is unreachable.
"""

import logging
import time

import cache
from config import settings
from exceptions import create_problem_response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("taskapi.ratelimit")


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = {"/health", "/ready", "/metrics", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Determine client identifier
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )

        client = cache._get_client()
        if client is None:
            # Degrade gracefully without blocking traffic when cache is unavailable
            return await call_next(request)

        now = time.time()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_requests
        key = f"ratelimit:{client_ip}"

        try:
            pipe = client.pipeline()
            # Remove timestamps older than current window
            pipe.zremrangebyscore(key, 0, now - window)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Count elements in window
            pipe.zcard(key)
            # Refresh TTL on key
            pipe.expire(key, window)
            _, _, current_count, _ = pipe.execute()

            remaining = max(0, limit - current_count)
            reset_seconds = window

            if current_count > limit:
                logger.warning("Rate limit exceeded for IP %s (%d requests)", client_ip, current_count)
                response = create_problem_response(
                    status_code=429,
                    title="Rate Limit Exceeded",
                    detail=f"Too many requests. Limit is {limit} requests per {window}s.",
                    error_code="RATE_LIMIT_EXCEEDED",
                    instance=request.url.path,
                    extra={"retry_after": reset_seconds, "limit": limit},
                )
                response.headers["Retry-After"] = str(reset_seconds)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(now + reset_seconds))
                return response

            response: Response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + reset_seconds))
            return response

        except Exception as exc:
            logger.warning("Rate limiter Redis error, failing open: %s", exc)
            return await call_next(request)
