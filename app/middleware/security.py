"""Security headers middleware for hardening HTTP responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces essential OWASP security headers across all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        if settings.enable_security_headers:
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
            if settings.app_env.lower() in ("production", "staging"):
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )

        return response
