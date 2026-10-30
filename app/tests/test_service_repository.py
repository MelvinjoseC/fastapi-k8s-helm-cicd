"""Unit tests for TaskRepository and TaskService layers."""

import pytest

import models
import schemas
from exceptions import TaskNotFoundError
from repositories.task_repository import TaskRepository
from services.task_service import TaskService


def test_repository_crud(db_session):
    repo = TaskRepository(db_session)

    # Create task
    task = repo.add(
        models.Task(
            title="Repository Pattern Test",
            description="Testing repo persistence directly",
            priority="high",
            status="pending",
        )
    )
    assert task.id is not None
    assert task.title == "Repository Pattern Test"

    # Query task
    fetched = repo.get_by_id(task.id)
    assert fetched is not None
    assert fetched.id == task.id

    # List tasks
    items = repo.list(priority="high")
    assert len(items) >= 1

    # Soft delete and restore
    repo.soft_delete(task)
    assert task.is_deleted is True
    assert repo.get_by_id(task.id, include_deleted=False) is None
    assert repo.get_by_id(task.id, include_deleted=True) is not None

    repo.restore(task)
    assert task.is_deleted is False


def test_service_create_and_update(db_session):
    service = TaskService(db_session)

    payload = schemas.TaskCreate(
        title="Service Layer Task",
        description="Business logic testing",
        priority=schemas.TaskPriority.URGENT,
        estimated_hours=6.5,
        assigned_to="developer@local",
    )
    created = service.create_task(payload)
    assert created.id is not None
    assert created.estimated_hours == 6.5
    assert created.assigned_to == "developer@local"

    # Update task
    updated = service.update_task(
        created.id,
        schemas.TaskUpdate(completed=True, actual_hours=5.0),
    )
    assert updated.completed is True
    assert updated.status == "completed"
    assert updated.actual_hours == 5.0


def test_service_missing_task_raises_domain_exception(db_session):
    service = TaskService(db_session)
    with pytest.raises(TaskNotFoundError):
        service.get_task(999999)

    with pytest.raises(TaskNotFoundError):
        service.update_task(999999, schemas.TaskUpdate(title="Nonexistent"))

    with pytest.raises(TaskNotFoundError):
        service.delete_task(999999)
