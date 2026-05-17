"""Chat Pydantic schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SuggestedAction(BaseModel):
    label: str
    message: str
    agent_hint: Optional[str] = None
    icon: Optional[str] = "zap"


class EmailDraftPayload(BaseModel):
    draft_id: str
    to: Optional[str] = None
    subject: Optional[str] = None
    body_preview: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_used: Optional[str] = None
    agent_display_name: Optional[str] = None
    download_url: Optional[str] = None
    agents_pipeline: Optional[list[str]] = None
    suggested_actions: Optional[list[SuggestedAction]] = None
    email_draft: Optional[EmailDraftPayload] = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageOut]
