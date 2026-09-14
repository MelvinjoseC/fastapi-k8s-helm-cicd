"""Request context and correlation ID tracking middleware.
Injects unique X-Request-ID and tracks request duration.
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from logging_config import correlation_id_ctx

logger = logging.getLogger("taskapi.request")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = correlation_id_ctx.set(request_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = str(duration_ms)

            # Do not log health/metrics checks at info level to reduce noise
            if request.url.path not in ("/health", "/metrics"):
                logger.info(
                    "%s %s - %d (%.2fms)",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Unhandled error processing %s %s (%.2fms)",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        finally:
            correlation_id_ctx.reset(token)
