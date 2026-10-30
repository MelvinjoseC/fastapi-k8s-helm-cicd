"""SQLAlchemy database models for Task management domain."""

from datetime import UTC, datetime
from enum import Enum

from database import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text


def utcnow():
    return datetime.now(UTC)


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False, index=True)
    status = Column(String(20), default=TaskStatus.PENDING.value, nullable=False, index=True)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value, nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    tags = Column(String(500), nullable=True, default="")
    created_by = Column(String(100), nullable=True, default="system")
    assigned_to = Column(String(100), nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
