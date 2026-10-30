"""Operational health, readiness, and diagnostics probes for Kubernetes."""

import os
import platform
import time
from typing import Annotated, Any

import cache
from config import settings
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(tags=["meta"])
_START_TIME = time.time()


@router.get("/health")
@router.get("/health/live")
def health() -> dict[str, str]:
    """Liveness probe: verifies process is responsive with zero external dependencies."""
    return {"status": "ok"}


@router.get("/ready")
@router.get("/health/ready")
def ready(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Readiness probe: verifies database connectivity and cache status."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {
        "status": "ready",
        "cache": "connected" if cache.ping() else "degraded",
    }


@router.get("/health/startup")
def startup(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Startup probe: verifies database initialization complete."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "initialized"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="startup initialization pending",
        ) from exc


@router.get("/health/system")
def system_diagnostics() -> dict[str, Any]:
    """Provides system diagnostics, runtime metrics, and environment summary."""
    uptime_seconds = round(time.time() - _START_TIME, 2)
    return {
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "process_id": os.getpid(),
        "cache_enabled": settings.cache_enabled,
        "rate_limit_enabled": settings.rate_limit_enabled,
    }
