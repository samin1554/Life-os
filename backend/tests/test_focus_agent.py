"""Tests for Focus Agent."""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock

from sqlalchemy import select

from agents.focus import run_focus_agent
from models import User, Task, Goal

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def focus_user(db_session):
    user = User(
        email=f"focus_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Focus Test",
        clerk_id=f"clerk_focus_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add tasks
    t1 = Task(user_id=user.id, title="Finish report", status="pending", priority=3, estimated_minutes=60)
    t2 = Task(user_id=user.id, title="Email team", status="in_progress", priority=2)
    t3 = Task(user_id=user.id, title="Old done task", status="completed")
    db_session.add_all([t1, t2, t3])

    # Add goal
    g = Goal(user_id=user.id, title="Get promoted", domain="career", progress_pct=30)
    db_session.add(g)

    await db_session.commit()
    yield user


async def test_focus_agent_returns_response(focus_user, db_session):
    mock_chat = AsyncMock(return_value="You should finish the report first.")

    with patch("agents.focus.chat_completion", mock_chat):
        result = await run_focus_agent("What should I do now?", str(focus_user.id), db_session)

    assert result["agent"] == "focus"
    assert "report" in result["response"].lower()
    assert result["pending_count"] >= 2


async def test_focus_agent_with_empty_tasks(focus_user, db_session):
    # Create user with no tasks
    user2 = User(
        email=f"focus_empty_{uuid.uuid4().hex[:8]}@example.com",
        name="Empty",
        clerk_id=f"clerk_empty_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    mock_chat = AsyncMock(return_value="You have no pending tasks. Great time to plan!")

    with patch("agents.focus.chat_completion", mock_chat):
        result = await run_focus_agent("What's next?", str(user2.id), db_session)

    assert result["agent"] == "focus"
    assert result["pending_count"] == 0
