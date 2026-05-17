"""Test Onboarding Agent."""
import uuid
from unittest.mock import patch, AsyncMock
import pytest
import pytest_asyncio
from sqlalchemy import select

from agents.onboarding import (
    process_onboarding_message,
    ONBOARDING_QUESTIONS,
    _extract_list,
    _extract_names,
)
from core.redis_client import delete_onboarding_state
from models import User


@pytest_asyncio.fixture(loop_scope="session")
async def onboarding_user_id(db_session):
    """Create a test user and yield their ID."""
    user = User(
        email=f"onboarding_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        clerk_id=f"clerk_test_{uuid.uuid4().hex[:8]}",
        onboarding_done=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    user_id = str(user.id)

    delete_onboarding_state(user_id)
    yield user_id
    delete_onboarding_state(user_id)


@pytest.mark.asyncio(loop_scope="session")
async def test_onboarding_start_returns_first_question(onboarding_user_id, db_session):
    result = await process_onboarding_message(onboarding_user_id, "", db_session)

    assert result["step"] == 1
    assert result["total_steps"] == 10
    assert result["complete"] is False
    assert "glad you're here" in result["message"].lower() or "name" in result["message"].lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_onboarding_advances_through_steps(onboarding_user_id, db_session):
    # Step 1
    result = await process_onboarding_message(onboarding_user_id, "", db_session)
    assert result["step"] == 1

    # Answer step 1
    result = await process_onboarding_message(onboarding_user_id, "My name is Sam. I'm here because I feel overwhelmed.", db_session)
    assert result["step"] == 2
    assert result["complete"] is False

    # Answer step 2
    result = await process_onboarding_message(onboarding_user_id, "I keep avoiding emails and admin tasks.", db_session)
    assert result["step"] == 3


@pytest.mark.asyncio(loop_scope="session")
async def test_onboarding_completes(onboarding_user_id, db_session):
    # Mock LLM calls to avoid HTTP traffic
    mock_extract = AsyncMock(return_value=[
        {"content": "User feels overwhelmed", "category": "wellbeing_baseline", "confidence": 0.9}
    ])
    mock_chat = AsyncMock(return_value="Here's what I've gathered about you so far.")

    with patch("agents.onboarding.extract_structured", mock_extract), \
         patch("agents.onboarding.chat_completion", mock_chat):

        # Fast-forward through all 10 steps
        await process_onboarding_message(onboarding_user_id, "", db_session)  # step 1

        answers = [
            "I'm Sam, feeling overwhelmed.",
            "I avoid emails.",
            "Work and health.",
            "A day with no urgent emails.",
            "Waking up late derails me.",
            "I'm sharpest in the morning.",
            "My sister Maria and my friend Alex.",
            "I want to learn guitar.",
            "I prefer gentle communication.",
            "Yes, that sounds right!",
        ]

        for answer in answers:
            result = await process_onboarding_message(onboarding_user_id, answer, db_session)

        assert result["complete"] is True
        assert "ready" in result["message"].lower() or "let's" in result["message"].lower()


def test_extract_list():
    assert _extract_list("health, work, relationships") == ["health", "work", "relationships"]
    assert _extract_list("health") == ["health"]
    assert _extract_list("") == []


def test_extract_names():
    names = _extract_names("My sister Maria and my friend Alex Smith")
    assert "Maria" in names
    assert "Alex Smith" in names
