"""
Task Management API.

A small, deliberately realistic service used to demonstrate a full
DevOps/Python workflow: containerization, Kubernetes deployment, CI/CD,
and observability.
"""

import logging
from contextlib import asynccontextmanager

import cache
from config import settings
from database import get_db, init_db
from exceptions import AppException, app_exception_handler
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from logging_config import setup_logging
from middleware.request_context import RequestCorrelationMiddleware
from middleware.security import SecurityHeadersMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from rate_limiter import RateLimiterMiddleware
from routers.tasks import router as tasks_router
from sqlalchemy import text
from sqlalchemy.orm import Session
from tracing import setup_tracing

setup_logging(settings.log_level, settings.log_format)
logger = logging.getLogger("taskapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    init_db()
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title="Task API",
    description="Demo microservice for a Kubernetes/DevOps portfolio project",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestCorrelationMiddleware)
app.add_exception_handler(AppException, app_exception_handler)

setup_tracing(app)

Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/health", tags=["meta"])
def health():
    """Liveness probe: process is up."""
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness probe: verifies database and cache connectivity."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "cache": "connected" if cache.ping() else "degraded"}


app.include_router(tasks_router)
