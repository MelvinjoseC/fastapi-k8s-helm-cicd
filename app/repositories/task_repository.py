"""Task repository encapsulating persistence and queries for Task entities."""

from datetime import datetime

from models import Task, utcnow
from sqlalchemy.orm import Session

from repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(db, Task)

    def get_by_id(self, task_id: int, include_deleted: bool = False) -> Task | None:
        query = self.db.query(Task).filter(Task.id == task_id)
        if not include_deleted:
            query = query.filter(Task.is_deleted == False)  # noqa: E712
        return query.first()

    def list(
        self,
        completed: bool | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        q: str | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        offset: int = 0,
        limit: int | None = None,
    ) -> list[Task]:
        query = self._build_filtered_query(
            completed=completed,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_before=due_before,
            due_after=due_after,
            q=q,
            include_deleted=include_deleted,
        )

        order_col = getattr(Task, sort_by, Task.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def count(
        self,
        completed: bool | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        q: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        query = self._build_filtered_query(
            completed=completed,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_before=due_before,
            due_after=due_after,
            q=q,
            include_deleted=include_deleted,
        )
        return query.count()

    def soft_delete(self, task: Task) -> Task:
        task.is_deleted = True
        task.deleted_at = utcnow()
        self.db.commit()
        return task

    def restore(self, task: Task) -> Task:
        task.is_deleted = False
        task.deleted_at = None
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_analytics_counts(self) -> dict:
        total = self.db.query(Task).filter(Task.is_deleted == False).count()  # noqa: E712
        completed = self.db.query(Task).filter(Task.is_deleted == False, Task.completed == True).count()  # noqa: E712
        active = total - completed

        now = utcnow()
        overdue = (
            self.db.query(Task)
            .filter(
                Task.is_deleted == False,  # noqa: E712
                Task.completed == False,  # noqa: E712
                Task.due_date.is_not(None),
                Task.due_date < now,
            )
            .count()
        )

        from sqlalchemy import func

        status_rows = (
            self.db.query(Task.status, func.count(Task.id))
            .filter(Task.is_deleted == False)  # noqa: E712
            .group_by(Task.status)
            .all()
        )
        status_dist = {str(st): cnt for st, cnt in status_rows}

        priority_rows = (
            self.db.query(Task.priority, func.count(Task.id))
            .filter(Task.is_deleted == False)  # noqa: E712
            .group_by(Task.priority)
            .all()
        )
        priority_dist = {str(pr): cnt for pr, cnt in priority_rows}

        return {
            "total_tasks": total,
            "active_tasks": active,
            "completed_tasks": completed,
            "overdue_tasks": overdue,
            "status_distribution": status_dist,
            "priority_distribution": priority_dist,
        }

    def _build_filtered_query(
        self,
        completed: bool | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        q: str | None = None,
        include_deleted: bool = False,
    ):
        query = self.db.query(Task)
        if not include_deleted:
            query = query.filter(Task.is_deleted == False)  # noqa: E712
        if completed is not None:
            query = query.filter(Task.completed == completed)
        if status is not None:
            query = query.filter(Task.status == status)
        if priority is not None:
            query = query.filter(Task.priority == priority)
        if assigned_to is not None:
            query = query.filter(Task.assigned_to == assigned_to)
        if due_before is not None:
            query = query.filter(Task.due_date <= due_before)
        if due_after is not None:
            query = query.filter(Task.due_date >= due_after)
        if q is not None:
            search_fmt = f"%{q}%"
            query = query.filter(
                (Task.title.ilike(search_fmt)) | (Task.description.ilike(search_fmt))
            )
        return query
