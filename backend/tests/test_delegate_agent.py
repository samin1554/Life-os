"""Tests for the Delegate Agent."""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_delegate_agent_returns_response(db_session):
    from agents.delegate import run_delegate_agent

    mock_ctx = {
        "user": None, "profile": None,
        "tasks": [], "checkins": [], "goals": [],
    }

    with patch("agents.delegate.get_user_context", new_callable=AsyncMock, return_value=mock_ctx), \
         patch("agents.delegate.chat_completion", new_callable=AsyncMock, return_value="Here are 3 beginner guitar books:\n1. Hal Leonard\n2. Alfred's\n3. Fender Play"):
        result = await run_delegate_agent("Find the best beginner guitar books", "test-user", db_session)

    assert result["agent"] == "delegate"
    assert "guitar" in result["response"].lower()


async def test_delegate_agent_research_output(db_session):
    from agents.delegate import run_delegate_agent

    mock_ctx = {
        "user": None, "profile": None,
        "tasks": [], "checkins": [], "goals": [],
    }

    with patch("agents.delegate.get_user_context", new_callable=AsyncMock, return_value=mock_ctx), \
         patch("agents.delegate.chat_completion", new_callable=AsyncMock, return_value="Here's a 90-day workout plan."):
        result = await run_delegate_agent("Write me a 90-day workout plan", "test-user", db_session)

    assert result["agent"] == "delegate"
    assert isinstance(result["response"], str)
