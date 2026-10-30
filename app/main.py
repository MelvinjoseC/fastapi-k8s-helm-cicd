"""
Task Management API.

A small, deliberately realistic service used to demonstrate a full
DevOps/Python workflow: containerization, Kubernetes deployment, CI/CD,
and observability.
"""

import logging
from contextlib import asynccontextmanager

from config import settings
from database import init_db
from exceptions import AppException, app_exception_handler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging_config import setup_logging
from middleware.request_context import RequestCorrelationMiddleware
from middleware.security import SecurityHeadersMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from rate_limiter import RateLimiterMiddleware
from routers.health import router as health_router
from routers.tasks import router as tasks_router
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

app.include_router(health_router)
app.include_router(tasks_router)
