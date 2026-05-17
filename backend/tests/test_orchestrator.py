"""Tests for Chat Orchestrator."""
import pytest
import uuid
from unittest.mock import patch, AsyncMock

from agents.orchestrator import process_chat, process_chat_streaming

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_process_chat_single_agent():
    mock_intent = {"agents": ["focus"], "order": "sequential", "reason": "Test"}
    mock_focus = {"agent": "focus", "response": "Do the thing."}

    with patch("agents.orchestrator.classify_intent", AsyncMock(return_value=mock_intent)), \
         patch.dict("agents.orchestrator.AGENT_RUNNERS", {"focus": AsyncMock(return_value=mock_focus)}):
        result = await process_chat("What next?", str(uuid.uuid4()), None)

    assert result["response"] == "Do the thing."
    assert result["agents_used"] == ["focus"]
    assert len(result["agent_outputs"]) == 1


async def test_process_chat_multi_agent_synthesis():
    mock_intent = {"agents": ["focus", "health"], "order": "sequential", "reason": "Test"}
    mock_focus = {"agent": "focus", "response": "Work."}
    mock_health = {"agent": "health", "response": "Rest."}
    mock_synthesis = {"agent": "synthesis", "response": "Balance work and rest."}

    with patch("agents.orchestrator.classify_intent", AsyncMock(return_value=mock_intent)), \
         patch.dict("agents.orchestrator.AGENT_RUNNERS", {
             "focus": AsyncMock(return_value=mock_focus),
             "health": AsyncMock(return_value=mock_health),
         }), \
         patch("agents.orchestrator.run_synthesis_agent", AsyncMock(return_value=mock_synthesis)):
        result = await process_chat("I'm overwhelmed", str(uuid.uuid4()), None)

    assert result["response"] == "Balance work and rest."
    assert "focus" in result["agents_used"]
    assert "health" in result["agents_used"]
    assert len(result["agent_outputs"]) == 2


async def test_process_chat_streaming_events():
    mock_intent = {"agents": ["focus"], "order": "sequential", "reason": "Test"}
    mock_focus = {"agent": "focus", "response": "Do it."}

    with patch("agents.orchestrator.classify_intent", AsyncMock(return_value=mock_intent)), \
         patch.dict("agents.orchestrator.AGENT_RUNNERS", {"focus": AsyncMock(return_value=mock_focus)}):
        events = []
        async for event in process_chat_streaming("What next?", str(uuid.uuid4()), None):
            events.append(event)

    assert events[0]["event"] == "intent"
    assert events[1]["event"] == "agent_start"
    assert events[2]["event"] == "agent_done"
    assert events[3]["event"] == "final"
    assert events[3]["data"]["response"] == "Do it."
