"""Onboarding routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from core.redis_client import get_onboarding_state, delete_onboarding_state
from models import User
from agents.onboarding import process_onboarding_message

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingMessageRequest(BaseModel):
    session_id: str | None = None
    message: str


class OnboardingStatusResponse(BaseModel):
    complete: bool
    step: int
    total_steps: int


class OnboardingMessageResponse(BaseModel):
    message: str
    step: int
    total_steps: int
    complete: bool


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(current_user: User = Depends(get_current_user)):
    """Get current onboarding status for the authenticated user."""
    state = get_onboarding_state(str(current_user.id))
    return {
        "complete": state.get("complete", False),
        "step": state.get("step", 0),
        "total_steps": state.get("total_steps", 10),
    }


@router.post("/start", response_model=OnboardingMessageResponse)
async def onboarding_start(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start the onboarding interview. Returns the first question."""
    if current_user.onboarding_done:
        return {
            "message": "You've already completed onboarding. Welcome back!",
            "step": 10,
            "total_steps": 10,
            "complete": True,
        }

    # Reset any existing onboarding state
    delete_onboarding_state(str(current_user.id))

    result = await process_onboarding_message(
        user_id=str(current_user.id),
        message="",  # Empty message triggers the first question
        db=db,
    )
    return result


@router.post("/message", response_model=OnboardingMessageResponse)
async def onboarding_message(
    req: OnboardingMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message during onboarding and receive the next question/response."""
    if current_user.onboarding_done:
        return {
            "message": "You've already completed onboarding. Welcome back!",
            "step": 10,
            "total_steps": 10,
            "complete": True,
        }

    result = await process_onboarding_message(
        user_id=str(current_user.id),
        message=req.message,
        db=db,
    )
    return result
