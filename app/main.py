"""
Task Management API.

A small, deliberately realistic service used to demonstrate a full
DevOps/Python workflow: containerization, Kubernetes deployment, CI/CD,
and observability. Endpoints:

  CRUD          POST/GET/PUT/DELETE /tasks
  Liveness      GET /health   - is the process alive? (no external calls)
  Readiness     GET /ready    - can it actually serve traffic? (checks DB)
  Metrics       GET /metrics  - Prometheus scrape target
"""
import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

import cache
import models
import schemas
from config import settings
from database import get_db, init_db
from logging_config import setup_logging

setup_logging(settings.log_level, settings.log_format)
logger = logging.getLogger("taskapi")

CACHE_KEY_ALL_TASKS = "tasks:all"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    init_db()
    yield
    logger.info("Shutting down %s", settings.app_name)


from fastapi.middleware.cors import CORSMiddleware
from exceptions import AppException, app_exception_handler
from middleware.request_context import RequestCorrelationMiddleware
from middleware.security import SecurityHeadersMiddleware

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
app.add_middleware(RequestCorrelationMiddleware)
app.add_exception_handler(AppException, app_exception_handler)

# Exposes /metrics in Prometheus exposition format (request counts,
# latency histograms, in-progress requests, etc.) with zero manual wiring.
Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/health", tags=["meta"])
def health():
    """Liveness probe: process is up. Deliberately has no external calls
    so a slow DB/Redis never causes Kubernetes to kill a healthy pod."""
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness probe: can this pod actually serve traffic? Checked
    separately from liveness so Kubernetes stops routing to a pod whose
    DB connection is broken without restarting the whole container."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - intentionally broad for a health check
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "cache": "connected" if cache.ping() else "degraded"}


@app.post("/tasks", response_model=schemas.TaskOut, status_code=201, tags=["tasks"])
def create_task(payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    task = models.Task(title=payload.title, description=payload.description)
    db.add(task)
    db.commit()
    db.refresh(task)
    cache.invalidate(CACHE_KEY_ALL_TASKS)
    return task


@app.get("/tasks", response_model=List[schemas.TaskOut], tags=["tasks"])
def list_tasks(
    completed: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if completed is None:
        cached = cache.get(CACHE_KEY_ALL_TASKS)
        if cached is not None:
            return cached

    query = db.query(models.Task)
    if completed is not None:
        query = query.filter(models.Task.completed == completed)
    tasks = query.order_by(models.Task.created_at.desc()).all()

    if completed is None:
        cache.set(CACHE_KEY_ALL_TASKS, [schemas.TaskOut.model_validate(t).model_dump() for t in tasks])
    return tasks


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    cache.invalidate(CACHE_KEY_ALL_TASKS)
    return task


@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    db.delete(task)
    db.commit()
    cache.invalidate(CACHE_KEY_ALL_TASKS)
    return None
