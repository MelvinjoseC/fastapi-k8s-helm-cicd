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

import cache
import metrics
import models
import schemas
from config import settings
from database import get_db, init_db
from fastapi import Depends, FastAPI, HTTPException, Query
from logging_config import setup_logging
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

setup_logging(settings.log_level, settings.log_format)
logger = logging.getLogger("taskapi")

CACHE_KEY_ALL_TASKS = "tasks:all"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    init_db()
    yield
    logger.info("Shutting down %s", settings.app_name)


from exceptions import AppException, app_exception_handler
from fastapi.middleware.cors import CORSMiddleware
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
from rate_limiter import RateLimiterMiddleware

app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestCorrelationMiddleware)
app.add_exception_handler(AppException, app_exception_handler)

from tracing import setup_tracing

setup_tracing(app)

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
    tags_str = ",".join(payload.tags) if payload.tags else ""
    task = models.Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority.value if hasattr(payload.priority, "value") else payload.priority,
        status=models.TaskStatus.PENDING.value,
        due_date=payload.due_date,
        tags=tags_str,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    cache.invalidate(CACHE_KEY_ALL_TASKS)
    metrics.tasks_created_total.labels(priority=task.priority).inc()
    metrics.active_tasks_gauge.inc()
    return task


@app.get("/tasks", response_model=list[schemas.TaskOut], tags=["tasks"])
def list_tasks(
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search term in title or description"),
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    # Only cache un-filtered queries
    if completed is None and status is None and priority is None and q is None and not include_deleted:
        cached = cache.get(CACHE_KEY_ALL_TASKS)
        if cached is not None:
            return cached

    query = db.query(models.Task)
    if not include_deleted:
        query = query.filter(models.Task.is_deleted == False)  # noqa: E712
    if completed is not None:
        query = query.filter(models.Task.completed == completed)
    if status is not None:
        query = query.filter(models.Task.status == status)
    if priority is not None:
        query = query.filter(models.Task.priority == priority)
    if q is not None:
        search_fmt = f"%{q}%"
        query = query.filter(
            (models.Task.title.ilike(search_fmt)) | (models.Task.description.ilike(search_fmt))
        )

    tasks = query.order_by(models.Task.created_at.desc()).all()

    if completed is None and status is None and priority is None and q is None and not include_deleted:
        cache.set(CACHE_KEY_ALL_TASKS, [schemas.TaskOut.model_validate(t).model_dump() for t in tasks])
    return tasks


@app.get("/tasks/paginated", response_model=schemas.PaginatedResponse[schemas.TaskOut], tags=["tasks"])
def list_tasks_paginated(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Task).filter(models.Task.is_deleted == False)  # noqa: E712
    if completed is not None:
        query = query.filter(models.Task.completed == completed)
    if status is not None:
        query = query.filter(models.Task.status == status)
    if priority is not None:
        query = query.filter(models.Task.priority == priority)
    if q is not None:
        search_fmt = f"%{q}%"
        query = query.filter(
            (models.Task.title.ilike(search_fmt)) | (models.Task.description.ilike(search_fmt))
        )

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = (
        query.order_by(models.Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )

    return schemas.PaginatedResponse(
        items=[schemas.TaskOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    cached = cache.get(cache.task_detail_key(task_id))
    if cached is not None:
        return cached

    task = db.get(models.Task, task_id)
    if task is None or task.is_deleted:
        raise HTTPException(status_code=404, detail="task not found")

    out = schemas.TaskOut.model_validate(task)
    cache.set(cache.task_detail_key(task_id), out.model_dump())
    return task


@app.put("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None or task.is_deleted:
        raise HTTPException(status_code=404, detail="task not found")

    data = payload.model_dump(exclude_unset=True)
    if "tags" in data and data["tags"] is not None:
        data["tags"] = ",".join(data["tags"])
    if "completed" in data:
        data["status"] = (
            models.TaskStatus.COMPLETED.value if data["completed"] else models.TaskStatus.PENDING.value
        )
    elif "status" in data and data["status"] is not None:
        data["completed"] = data["status"] == models.TaskStatus.COMPLETED.value

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    cache.invalidate_task(task_id)
    if task.completed:
        metrics.tasks_completed_total.inc()
    return task


@app.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: int, permanent: bool = Query(default=False), db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None or (task.is_deleted and not permanent):
        raise HTTPException(status_code=404, detail="task not found")

    if permanent:
        db.delete(task)
    else:
        task.is_deleted = True
        task.deleted_at = models.utcnow()

    db.commit()
    cache.invalidate_task(task_id)
    metrics.tasks_deleted_total.labels(permanent=str(permanent).lower()).inc()
    if not task.completed:
        metrics.active_tasks_gauge.dec()
    return None


@app.post("/tasks/{task_id}/restore", response_model=schemas.TaskOut, tags=["tasks"])
def restore_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if task is None or not task.is_deleted:
        raise HTTPException(status_code=404, detail="task not found or not deleted")

    task.is_deleted = False
    task.deleted_at = None
    db.commit()
    db.refresh(task)
    cache.invalidate_task(task_id)
    if not task.completed:
        metrics.active_tasks_gauge.inc()
    return task
