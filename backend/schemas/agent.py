"""Agent Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentRunRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=2000)
    task_id: Optional[UUID] = None


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_name: Optional[str]
    status: str
    input_summary: Optional[str]
    output_summary: Optional[str]
    full_response: Optional[str] = None
    trigger_type: Optional[str]
    task_id: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    accepted: Optional[bool]
    overridden: bool
    override_note: Optional[str]
    created_at: datetime


class AgentRunListResponse(BaseModel):
    runs: list[AgentRunResponse]
    total: int


class AgentStatusCard(BaseModel):
    name: str
    display_name: str
    status: str
    last_run_at: Optional[datetime]
    last_output_summary: Optional[str]
    runs_today: int


class AgentStatusResponse(BaseModel):
    agents: list[AgentStatusCard]


class AgentFeedbackRequest(BaseModel):
    accepted: bool
    override_note: Optional[str] = None
