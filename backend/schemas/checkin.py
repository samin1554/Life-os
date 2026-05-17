"""CheckIn Pydantic schemas."""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CheckInBase(BaseModel):
    checkin_type: str = Field(..., pattern=r"^(morning|midday|evening)$")
    checkin_date: date
    mood_score: Optional[int] = Field(default=None, ge=1, le=5)
    energy_score: Optional[int] = Field(default=None, ge=1, le=5)
    stress_score: Optional[int] = Field(default=None, ge=1, le=5)
    focus_score: Optional[int] = Field(default=None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=5)
    exercised: Optional[bool] = None
    notes: Optional[str] = None
    wins: Optional[List[str]] = None
    struggles: Optional[List[str]] = None
    tasks_planned: Optional[int] = Field(default=None, ge=0)
    tasks_completed: Optional[int] = Field(default=None, ge=0)


class CheckInCreate(CheckInBase):
    pass


class CheckInUpdate(BaseModel):
    checkin_type: Optional[str] = Field(default=None, pattern=r"^(morning|midday|evening)$")
    checkin_date: Optional[date] = None
    mood_score: Optional[int] = Field(default=None, ge=1, le=5)
    energy_score: Optional[int] = Field(default=None, ge=1, le=5)
    stress_score: Optional[int] = Field(default=None, ge=1, le=5)
    focus_score: Optional[int] = Field(default=None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    sleep_quality: Optional[int] = Field(default=None, ge=1, le=5)
    exercised: Optional[bool] = None
    notes: Optional[str] = None
    wins: Optional[List[str]] = None
    struggles: Optional[List[str]] = None
    tasks_planned: Optional[int] = Field(default=None, ge=0)
    tasks_completed: Optional[int] = Field(default=None, ge=0)


class CheckInResponse(CheckInBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime


class CheckInListResponse(BaseModel):
    checkins: list[CheckInResponse]
    total: int
