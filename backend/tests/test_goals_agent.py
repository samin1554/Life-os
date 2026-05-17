"""Tests for the Goals Agent."""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_goals_agent_returns_response(db_session):
    from agents.goals import run_goals_agent

    mock_ctx = {
        "user": None, "profile": None,
        "tasks": [], "checkins": [], "goals": [],
    }

    with patch("agents.goals.get_user_context", new_callable=AsyncMock, return_value=mock_ctx), \
         patch("agents.goals.chat_completion", new_callable=AsyncMock, return_value="Focus on your top goal this week."):
        result = await run_goals_agent("How are my goals going?", "test-user", db_session)

    assert result["agent"] == "goals"
    assert "goal" in result["response"].lower()
    assert "goal_count" in result


async def test_goals_agent_with_existing_goals(db_session):
    from agents.goals import run_goals_agent
    from unittest.mock import MagicMock

    mock_goal = MagicMock()
    mock_goal.title = "Learn guitar"
    mock_goal.domain = "learning"
    mock_goal.progress_pct = 15

    mock_ctx = {
        "user": None, "profile": None,
        "tasks": [], "checkins": [], "goals": [mock_goal],
    }

    with patch("agents.goals.get_user_context", new_callable=AsyncMock, return_value=mock_ctx), \
         patch("agents.goals.chat_completion", new_callable=AsyncMock, return_value="Your guitar goal is at 15%."):
        result = await run_goals_agent("How's my guitar progress?", "test-user", db_session)

    assert result["goal_count"] == 1
