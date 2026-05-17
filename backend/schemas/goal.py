"""Goal Pydantic schemas."""
from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoalBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    why: Optional[str] = None
    domain: Optional[str] = Field(default=None, pattern=r"^(health|career|work|relationships|learning|personal|finance)$")
    timeframe: Optional[str] = Field(default=None, pattern=r"^(this_week|this_month|this_year|annual|long_term)$")


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    why: Optional[str] = None
    domain: Optional[str] = Field(default=None, pattern=r"^(health|career|work|relationships|learning|personal|finance)$")
    timeframe: Optional[str] = Field(default=None, pattern=r"^(this_week|this_month|this_year|annual|long_term)$")
    status: Optional[str] = Field(default=None, pattern=r"^(active|completed|paused|abandoned)$")
    progress_pct: Optional[int] = Field(default=None, ge=0, le=100)
    milestones: Optional[Union[list[dict[str, Any]], dict[str, Any]]] = None


class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: str
    progress_pct: int
    last_action_at: Optional[datetime] = None
    milestones: Optional[Union[list[dict[str, Any]], dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    total: int
