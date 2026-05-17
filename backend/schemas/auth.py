from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    timezone: str
    onboarding_done: bool
    created_at: datetime


class ClerkWebhookPayload(BaseModel):
    type: str
    data: dict
