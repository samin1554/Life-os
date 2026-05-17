"""Tests for Synthesis Agent."""
import pytest
from unittest.mock import patch, AsyncMock

from agents.synthesis import run_synthesis_agent

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_synthesis_combines_outputs():
    mock_chat = AsyncMock(return_value="Here's your plan: focus on the report first, then take a walk.")

    agent_outputs = [
        {"agent": "focus", "response": "Finish the report."},
        {"agent": "health", "response": "You need more sleep."},
    ]

    with patch("agents.synthesis.chat_completion", mock_chat):
        result = await run_synthesis_agent(
            "What should I do today?",
            agent_outputs,
            user_name="Sam",
        )

    assert result["agent"] == "synthesis"
    assert "focus" in result["sources"]
    assert "health" in result["sources"]
    assert "report" in result["response"].lower()


async def test_synthesis_single_agent():
    mock_chat = AsyncMock(return_value="Just finish the report.")

    agent_outputs = [
        {"agent": "focus", "response": "Finish the report."},
    ]

    with patch("agents.synthesis.chat_completion", mock_chat):
        result = await run_synthesis_agent("What next?", agent_outputs)

    assert result["agent"] == "synthesis"
    assert result["sources"] == ["focus"]
