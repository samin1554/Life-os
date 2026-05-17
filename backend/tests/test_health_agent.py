"""Tests for Health Agent."""
import pytest
import pytest_asyncio
import uuid
from datetime import date
from unittest.mock import patch, AsyncMock

from agents.health import run_health_agent
from models import User, CheckIn

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def health_user(db_session):
    user = User(
        email=f"health_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Health Test",
        clerk_id=f"clerk_health_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add checkins
    c1 = CheckIn(user_id=user.id, checkin_type="morning", checkin_date=date.today(), mood_score=3, energy_score=2, sleep_hours=5.5, exercised=False)
    c2 = CheckIn(user_id=user.id, checkin_type="evening", checkin_date=date.today(), mood_score=4, energy_score=3, sleep_hours=7.0, exercised=True)
    db_session.add_all([c1, c2])
    await db_session.commit()
    yield user


async def test_health_agent_returns_response(health_user, db_session):
    mock_chat = AsyncMock(return_value="Your sleep has been inconsistent. Try a consistent bedtime.")

    with patch("agents.health.chat_completion", mock_chat):
        result = await run_health_agent("Why am I so tired?", str(health_user.id), db_session)

    assert result["agent"] == "health"
    assert result["checkin_count"] == 2
    assert "sleep" in result["response"].lower() or "tired" in result["response"].lower()


async def test_health_agent_no_checkins(db_session):
    user = User(
        email=f"health_empty_{uuid.uuid4().hex[:8]}@example.com",
        name="Empty",
        clerk_id=f"clerk_health_empty_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    mock_chat = AsyncMock(return_value="I don't have any check-in data yet. Start tracking!")

    with patch("agents.health.chat_completion", mock_chat):
        result = await run_health_agent("How am I doing?", str(user.id), db_session)

    assert result["agent"] == "health"
    assert result["checkin_count"] == 0
