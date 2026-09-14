"""Pydantic schemas and validation for the Task management API.
"""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import TaskPriority, TaskStatus

T = TypeVar("T")


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, examples=["Implement Helm Chart"])
    description: Optional[str] = Field(None, max_length=2000, examples=["Add values.schema.json and test hooks"])
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, examples=[TaskPriority.MEDIUM])
    due_date: Optional[datetime] = Field(None, examples=["2026-12-31T23:59:59Z"])
    tags: List[str] = Field(default_factory=list, examples=[["devops", "k8s"]])

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty or whitespace only")
        return v


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    status: str
    priority: str
    due_date: Optional[datetime] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v or []


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
