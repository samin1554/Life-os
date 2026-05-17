"""Tests for Chat router."""
import pytest
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_chat_non_streaming(client, auth_headers):
    with patch("routers.chat.chat_completion", AsyncMock(return_value="Focus on your top priority.")):
        resp = await client.post(
            "/chat",
            json={"message": "What should I do now?"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Focus on your top priority."
    assert "session_id" in data


async def test_chat_empty_message(client, auth_headers):
    resp = await client.post(
        "/chat",
        json={"message": "  "},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_chat_persists_messages(client, auth_headers):
    with patch("routers.chat.chat_completion", AsyncMock(return_value="Got it.")):
        resp = await client.post(
            "/chat",
            json={"message": "Remember this", "session_id": "00000000-0000-0000-0000-000000000001"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "00000000-0000-0000-0000-000000000001"

    history_resp = await client.get(
        "/chat/history?session_id=00000000-0000-0000-0000-000000000001",
        headers=auth_headers,
    )
    assert history_resp.status_code == 200
    messages = history_resp.json()["messages"]
    assert len(messages) >= 2
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


async def test_chat_with_session_continuity(client, auth_headers):
    with patch("routers.chat.chat_completion", AsyncMock(return_value="First reply.")):
        resp1 = await client.post(
            "/chat",
            json={"message": "Hello"},
            headers=auth_headers,
        )
    session_id = resp1.json()["session_id"]

    with patch("routers.chat.chat_completion", AsyncMock(return_value="Second reply.")) as mock_llm:
        resp2 = await client.post(
            "/chat",
            json={"message": "Follow up", "session_id": session_id},
            headers=auth_headers,
        )

    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == session_id
    call_args = mock_llm.call_args
    messages = call_args[0][1]
    assert any(m["content"] == "Hello" for m in messages)
