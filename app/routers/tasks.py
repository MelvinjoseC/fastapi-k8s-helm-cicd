"""Task management endpoints using TaskService and Repository abstractions."""

from typing import Annotated

import schemas
from config import settings
from database import get_db
from fastapi import APIRouter, Depends, Query, status
from services.task_service import TaskService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    return TaskService(db)


@router.post("", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: schemas.TaskCreate,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Create a new task."""
    return service.create_task(payload)


@router.post("/bulk", response_model=schemas.BulkTaskCreateResponse, status_code=status.HTTP_201_CREATED)
def bulk_create_tasks(
    payload: schemas.BulkTaskCreate,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Create multiple tasks in a single transaction."""
    return service.bulk_create(payload)


@router.patch("/bulk", response_model=schemas.BulkActionResponse)
def bulk_update_tasks(
    payload: schemas.BulkTaskUpdate,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Batch update status or priority for multiple tasks."""
    return service.bulk_update(payload)


@router.delete("/bulk", response_model=schemas.BulkActionResponse)
def bulk_delete_tasks(
    payload: schemas.BulkTaskDelete,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Batch soft or permanent delete for multiple tasks."""
    return service.bulk_delete(payload)


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search term in title or description"),
    include_deleted: bool = Query(default=False),
):
    """List all tasks with optional filters."""
    return service.list_tasks(
        completed=completed,
        status=status,
        priority=priority,
        q=q,
        include_deleted=include_deleted,
    )


@router.get("/paginated", response_model=schemas.PaginatedResponse[schemas.TaskOut])
def list_tasks_paginated(
    service: Annotated[TaskService, Depends(get_task_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """Retrieve a paginated list of tasks."""
    return service.list_tasks_paginated(
        page=page,
        page_size=page_size,
        completed=completed,
        status=status,
        priority=priority,
        q=q,
    )


@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(
    task_id: int,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Get task details by ID."""
    return service.get_task(task_id)


@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Update task fields."""
    return service.update_task(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    service: Annotated[TaskService, Depends(get_task_service)],
    permanent: bool = Query(default=False),
):
    """Soft delete or permanently delete a task."""
    service.delete_task(task_id, permanent=permanent)
    return None


@router.post("/{task_id}/restore", response_model=schemas.TaskOut)
def restore_task(
    task_id: int,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Restore a soft-deleted task."""
    return service.restore_task(task_id)
