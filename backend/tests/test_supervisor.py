"""Test Supervisor Agent."""
import pytest
from agents.supervisor import classify_intent

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_classify_overwhelm():
    result = await classify_intent("I'm completely overwhelmed and panicking, everything is piling up and I can't handle it")
    assert "chaos_triage" in result["agents"]


async def test_classify_execution():
    result = await classify_intent("Can you write an email to my boss asking for time off?")
    assert "execution" in result["agents"] or "delegate" in result["agents"]


async def test_classify_health():
    result = await classify_intent("I slept 4 hours and feel terrible")
    assert "health" in result["agents"]


async def test_classify_goals():
    result = await classify_intent("I want to learn guitar this year")
    assert "goals" in result["agents"]



async def test_classify_fallback():
    result = await classify_intent("What's on my plate today?")
    assert "focus" in result["agents"] or "none" in result["agents"]


async def test_classify_returns_valid_structure():
    result = await classify_intent("I need help with my daily plan")
    assert "agents" in result
    assert "order" in result
    assert "reason" in result
    assert isinstance(result["agents"], list)
    assert result["order"] in ("sequential", "parallel")
