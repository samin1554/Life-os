"""Tests for the task execute endpoint."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import uuid

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _mock_interaction(status="completed", output="Subject: Appointment Reschedule\n\nDear Dr Johnson..."):
    interaction = MagicMock()
    interaction.id = uuid.uuid4()
    interaction.status = status
    interaction.output_summary = output[:500]
    interaction.full_response = output
    return interaction


async def test_execute_task(client, auth_headers):
    create_resp = await client.post("/tasks", json={
        "title": "Email Dr Johnson about appointment",
        "description": "Reschedule to Thursday",
        "category": "email",
    }, headers=auth_headers)
    task_id = create_resp.json()["id"]

    mock_interaction = _mock_interaction()

    with patch("routers.tasks.execute_agent_run", new_callable=AsyncMock, return_value=mock_interaction):
        resp = await client.post(f"/tasks/{task_id}/execute", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] == "completed"


async def test_execute_task_not_found(client, auth_headers):
    with patch("routers.tasks.execute_agent_run", new_callable=AsyncMock):
        resp = await client.post("/tasks/00000000-0000-0000-0000-000000000000/execute", headers=auth_headers)
    assert resp.status_code == 404
