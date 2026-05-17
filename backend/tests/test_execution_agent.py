"""Tests for Execution Agent."""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch, AsyncMock

from agents.execution import run_execution_agent
from models import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def execution_user(db_session):
    user = User(
        email=f"exec_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Exec Test",
        clerk_id=f"clerk_exec_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


async def test_execution_agent_drafts_email(execution_user, db_session):
    mock_chat = AsyncMock(return_value="Subject: Time Off Request\n\nDear Boss...")

    with patch("agents.execution.chat_completion", mock_chat):
        result = await run_execution_agent(
            "Draft an email to my boss asking for time off next Friday",
            str(execution_user.id),
            db_session,
        )

    assert result["agent"] == "execution"
    assert result["output_type"] == "email"
    assert "boss" in result["response"].lower()


async def test_execution_agent_research_output_type(execution_user, db_session):
    mock_chat = AsyncMock(return_value="Here's what I found about productivity methods...")

    with patch("agents.execution.chat_completion", mock_chat):
        result = await run_execution_agent(
            "Research the best productivity methods for ADHD",
            str(execution_user.id),
            db_session,
        )

    assert result["agent"] == "execution"
    assert result["output_type"] == "research"
