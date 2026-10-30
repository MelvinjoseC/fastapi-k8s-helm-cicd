"""Task management endpoints using TaskService and Repository abstractions."""

import csv
import io
import json
from typing import Annotated

import schemas
from auth import get_current_user
from config import settings
from database import get_db
from fastapi import APIRouter, Depends, Query, Response, status
from services.task_service import TaskService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


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


@router.get("/analytics/summary", response_model=schemas.TaskAnalyticsSummary)
def get_task_analytics(
    service: Annotated[TaskService, Depends(get_task_service)],
):
    """Retrieve statistical analytics, completion rates, and status distributions."""
    raw = service.get_analytics()
    total = raw.get("total_tasks", 0)
    completed = raw.get("completed_tasks", 0)
    rate = round((completed / total) * 100, 2) if total > 0 else 0.0

    return schemas.TaskAnalyticsSummary(
        total_tasks=total,
        active_tasks=raw.get("active_tasks", 0),
        completed_tasks=completed,
        overdue_tasks=raw.get("overdue_tasks", 0),
        completion_rate_percent=rate,
        status_distribution=raw.get("status_distribution", {}),
        priority_distribution=raw.get("priority_distribution", {}),
    )


@router.get("/export")
def export_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    format: str = Query(default="json", pattern="^(json|csv)$"),
    include_deleted: bool = Query(default=False),
):
    """Export tasks to CSV or JSON format for reporting and backups."""
    tasks = service.list_tasks(include_deleted=include_deleted)
    task_dicts = [schemas.TaskOut.model_validate(t).model_dump(mode="json") for t in tasks]

    if format == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "title", "description", "completed", "status", "priority",
            "due_date", "tags", "created_by", "assigned_to", "estimated_hours",
            "actual_hours", "created_at", "updated_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for d in task_dicts:
            row = d.copy()
            row["tags"] = ";".join(d.get("tags") or [])
            writer.writerow(row)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="tasks.csv"'},
        )

    return Response(
        content=json.dumps(task_dicts, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="tasks.json"'},
    )


@router.get("", response_model=list[schemas.TaskOut])
def list_tasks(
    service: Annotated[TaskService, Depends(get_task_service)],
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search term in title or description"),
    sort_by: str = Query(default="created_at", description="Field to sort by"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    include_deleted: bool = Query(default=False),
):
    """List all tasks with optional filters."""
    return service.list_tasks(
        completed=completed,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        q=q,
        include_deleted=include_deleted,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/paginated", response_model=schemas.PaginatedResponse[schemas.TaskOut])
def list_tasks_paginated(
    service: Annotated[TaskService, Depends(get_task_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.default_page_size, ge=1, le=settings.max_page_size),
    completed: bool | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    assigned_to: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    q: str | None = Query(default=None),
):
    """Retrieve a paginated list of tasks."""
    return service.list_tasks_paginated(
        page=page,
        page_size=page_size,
        completed=completed,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        sort_by=sort_by,
        sort_order=sort_order,
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
