"""Domain exceptions and standardized RFC 7807 error response handlers.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base class for application domain exceptions."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.extra = extra or {}


class ResourceNotFoundError(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            detail=f"{resource} with id '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            extra={"resource": resource, "id": identifier},
        )


class ConflictError(AppException):
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
        )


class RateLimitExceededError(AppException):
    def __init__(self, retry_after: int):
        super().__init__(
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            extra={"retry_after": retry_after},
        )


def create_problem_response(
    status_code: int,
    title: str,
    detail: str,
    error_code: str,
    instance: str,
    extra: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    content = {
        "type": f"https://httpstatuses.com/{status_code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "error_code": error_code,
        "instance": instance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        content["extra"] = extra
    return JSONResponse(status_code=status_code, content=content)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return create_problem_response(
        status_code=exc.status_code,
        title=exc.error_code.replace("_", " ").title(),
        detail=exc.detail,
        error_code=exc.error_code,
        instance=request.url.path,
        extra=exc.extra,
    )
