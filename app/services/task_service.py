"""Domain service coordinating business logic, cache invalidation, and metrics for Tasks."""

import logging
from typing import Any

import cache
import metrics
import models
import schemas
from exceptions import TaskNotFoundError
from repositories.task_repository import TaskRepository
from sqlalchemy.orm import Session

logger = logging.getLogger("taskapi.service")
CACHE_KEY_ALL_TASKS = "tasks:all"


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)

    def create_task(self, payload: schemas.TaskCreate) -> models.Task:
        tags_str = ",".join(payload.tags) if payload.tags else ""
        priority_val = (
            payload.priority.value if hasattr(payload.priority, "value") else str(payload.priority)
        )

        task = models.Task(
            title=payload.title,
            description=payload.description,
            priority=priority_val,
            status=models.TaskStatus.PENDING.value,
            due_date=payload.due_date,
            tags=tags_str,
            created_by=payload.created_by or "system",
            assigned_to=payload.assigned_to,
            estimated_hours=payload.estimated_hours,
        )
        saved = self.repo.add(task)

        cache.invalidate(CACHE_KEY_ALL_TASKS)
        metrics.tasks_created_total.labels(priority=saved.priority).inc()
        metrics.active_tasks_gauge.inc()
        logger.info("Task created id=%d priority=%s", saved.id, saved.priority)
        return saved

    def bulk_create(self, payload: schemas.BulkTaskCreate) -> schemas.BulkTaskCreateResponse:
        created_tasks = []
        for item in payload.tasks:
            tags_str = ",".join(item.tags) if item.tags else ""
            priority_val = (
                item.priority.value if hasattr(item.priority, "value") else str(item.priority)
            )
            task = models.Task(
                title=item.title,
                description=item.description,
                priority=priority_val,
                status=models.TaskStatus.PENDING.value,
                due_date=item.due_date,
                tags=tags_str,
                created_by=item.created_by or "system",
                assigned_to=item.assigned_to,
                estimated_hours=item.estimated_hours,
            )
            self.db.add(task)
            created_tasks.append(task)

        self.db.commit()
        for t in created_tasks:
            self.db.refresh(t)
            metrics.tasks_created_total.labels(priority=t.priority).inc()
            metrics.active_tasks_gauge.inc()

        cache.invalidate(CACHE_KEY_ALL_TASKS)
        return schemas.BulkTaskCreateResponse(
            created_count=len(created_tasks),
            tasks=[schemas.TaskOut.model_validate(t) for t in created_tasks],
        )

    def bulk_update(self, payload: schemas.BulkTaskUpdate) -> schemas.BulkActionResponse:
        tasks = (
            self.db.query(models.Task)
            .filter(models.Task.id.in_(payload.task_ids), models.Task.is_deleted == False)  # noqa: E712
            .all()
        )
        for t in tasks:
            if payload.status is not None:
                t.status = payload.status.value if hasattr(payload.status, "value") else payload.status
                t.completed = t.status == models.TaskStatus.COMPLETED.value
            elif payload.completed is not None:
                t.completed = payload.completed
                t.status = (
                    models.TaskStatus.COMPLETED.value if payload.completed else models.TaskStatus.PENDING.value
                )
            if payload.priority is not None:
                t.priority = (
                    payload.priority.value if hasattr(payload.priority, "value") else payload.priority
                )
            cache.invalidate_task(t.id)

        self.db.commit()
        cache.invalidate(CACHE_KEY_ALL_TASKS)
        return schemas.BulkActionResponse(
            affected_count=len(tasks),
            message=f"Successfully updated {len(tasks)} tasks",
        )

    def bulk_delete(self, payload: schemas.BulkTaskDelete) -> schemas.BulkActionResponse:
        tasks = (
            self.db.query(models.Task)
            .filter(models.Task.id.in_(payload.task_ids))
            .all()
        )
        count = 0
        for t in tasks:
            if payload.permanent:
                self.db.delete(t)
            else:
                if not t.is_deleted:
                    t.is_deleted = True
                    t.deleted_at = models.utcnow()
                    if not t.completed:
                        metrics.active_tasks_gauge.dec()
            cache.invalidate_task(t.id)
            count += 1

        self.db.commit()
        cache.invalidate(CACHE_KEY_ALL_TASKS)
        return schemas.BulkActionResponse(
            affected_count=count,
            message=f"Successfully deleted {count} tasks",
        )

    def get_task(self, task_id: int) -> models.Task:
        cached = cache.get(cache.task_detail_key(task_id))
        if cached is not None:
            return models.Task(**cached) if isinstance(cached, dict) else cached

        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        out = schemas.TaskOut.model_validate(task)
        cache.set(cache.task_detail_key(task_id), out.model_dump())
        return task

    def list_tasks(
        self,
        completed: bool | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_before: Any = None,
        due_after: Any = None,
        q: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[models.Task]:
        is_default_query = (
            completed is None
            and status is None
            and priority is None
            and assigned_to is None
            and due_before is None
            and due_after is None
            and q is None
            and not include_deleted
            and sort_by == "created_at"
            and sort_order == "desc"
        )
        if is_default_query:
            cached = cache.get(CACHE_KEY_ALL_TASKS)
            if cached is not None:
                return cached

        tasks = self.repo.list(
            completed=completed,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_before=due_before,
            due_after=due_after,
            q=q,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        if is_default_query:
            cache.set(
                CACHE_KEY_ALL_TASKS,
                [schemas.TaskOut.model_validate(t).model_dump() for t in tasks],
            )
        return tasks

    def list_tasks_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        completed: bool | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_before: Any = None,
        due_after: Any = None,
        q: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> schemas.PaginatedResponse[schemas.TaskOut]:
        total = self.repo.count(
            completed=completed,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_before=due_before,
            due_after=due_after,
            q=q,
        )
        offset = (page - 1) * page_size
        items = self.repo.list(
            completed=completed,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_before=due_before,
            due_after=due_after,
            q=q,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=page_size,
        )
        total_pages = max(1, (total + page_size - 1) // page_size)

        return schemas.PaginatedResponse(
            items=[schemas.TaskOut.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def update_task(self, task_id: int, payload: schemas.TaskUpdate) -> models.Task:
        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

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

        updated = self.repo.update(task)
        cache.invalidate_task(task_id)
        if updated.completed:
            metrics.tasks_completed_total.inc()
        return updated

    def delete_task(self, task_id: int, permanent: bool = False) -> None:
        task = self.repo.get_by_id(task_id, include_deleted=permanent)
        if not task:
            raise TaskNotFoundError(task_id)

        if permanent:
            self.repo.delete(task)
        else:
            self.repo.soft_delete(task)

        cache.invalidate_task(task_id)
        metrics.tasks_deleted_total.labels(permanent=str(permanent).lower()).inc()
        if not task.completed:
            metrics.active_tasks_gauge.dec()

    def restore_task(self, task_id: int) -> models.Task:
        task = self.repo.get_by_id(task_id, include_deleted=True)
        if not task or not task.is_deleted:
            raise TaskNotFoundError(task_id)

        restored = self.repo.restore(task)
        cache.invalidate_task(task_id)
        if not restored.completed:
            metrics.active_tasks_gauge.inc()
        return restored

    def get_analytics(self) -> dict[str, Any]:
        return self.repo.get_analytics_counts()
