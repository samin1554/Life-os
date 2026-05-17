"""Task Pydantic schemas."""
from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    status: str = Field(default="pending", pattern=r"^(pending|in_progress|completed|cancelled)$")
    priority: int = Field(default=2, ge=1, le=5)
    due_date: Optional[date] = None
    scheduled_for: Optional[datetime] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    actual_minutes: Optional[int] = Field(default=None, ge=0)


class TaskCreate(TaskBase):
    assigned_agent: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern=r"^(pending|in_progress|completed|cancelled)$")
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    due_date: Optional[date] = None
    scheduled_for: Optional[datetime] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    actual_minutes: Optional[int] = Field(default=None, ge=0)
    assigned_agent: Optional[str] = None


class TaskAssignRequest(BaseModel):
    agent: str
    run_immediately: bool = False


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    times_deferred: int
    first_created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent: Optional[str] = None
    execution_output: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
