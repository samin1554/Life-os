"""Tests for Chaos Triage Agent."""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock

from agents.chaos_triage import run_chaos_triage_agent
from models import User, Task

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def chaos_user(db_session):
    user = User(
        email=f"chaos_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Chaos Test",
        clerk_id=f"clerk_chaos_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Many pending tasks
    for i in range(8):
        t = Task(user_id=user.id, title=f"Task {i+1}", status="pending", priority=2)
        db_session.add(t)
    await db_session.commit()
    yield user


async def test_chaos_triage_returns_response(chaos_user, db_session):
    mock_chat = AsyncMock(return_value="That sounds overwhelming. Let's pick just one thing.")
    mock_extract = AsyncMock(return_value={"items": ["Task 1", "Task 2", "Task 3"]})

    with patch("agents.chaos_triage.chat_completion", mock_chat), \
         patch("agents.chaos_triage.extract_structured", mock_extract):
        result = await run_chaos_triage_agent(
            "I have 12 things to do and I'm panicking",
            str(chaos_user.id),
            db_session,
        )

    assert result["agent"] == "chaos_triage"
    assert result["pending_count"] == 8
    assert isinstance(result["extracted_items"], list)


async def test_chaos_triage_no_items_extracted(chaos_user, db_session):
    mock_chat = AsyncMock(return_value="Let's take a breath.")
    mock_extract = AsyncMock(return_value={"items": []})

    with patch("agents.chaos_triage.chat_completion", mock_chat), \
         patch("agents.chaos_triage.extract_structured", mock_extract):
        result = await run_chaos_triage_agent(
            "I'm so overwhelmed",
            str(chaos_user.id),
            db_session,
        )

    assert result["agent"] == "chaos_triage"
    assert result["extracted_items"] == []
