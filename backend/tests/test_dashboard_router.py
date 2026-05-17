"""Tests for the dashboard router."""
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_dashboard_returns_structure(client, auth_headers):
    resp = await client.get("/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "today" in data
    assert "date" in data["today"]
    assert "pending_tasks" in data["today"]
    assert "checkin_done" in data["today"]
    assert "energy_level" in data["today"]

    assert "tasks" in data
    assert isinstance(data["tasks"], list)

    assert "streak" in data
    assert isinstance(data["streak"], int)

    assert "completed_this_week" in data
    assert "goals" in data
    assert "averages" in data
    assert "onboarding_done" in data


async def test_dashboard_reflects_tasks(client, auth_headers):
    await client.post("/tasks", json={"title": "Dashboard task"}, headers=auth_headers)

    resp = await client.get("/dashboard", headers=auth_headers)
    data = resp.json()
    assert data["today"]["pending_tasks"] >= 1
    task_titles = [t["title"] for t in data["tasks"]]
    assert "Dashboard task" in task_titles


async def test_dashboard_reflects_goals(client, auth_headers):
    await client.post("/goals", json={"title": "Dashboard goal", "domain": "health"}, headers=auth_headers)

    resp = await client.get("/dashboard", headers=auth_headers)
    data = resp.json()
    goal_titles = [g["title"] for g in data["goals"]]
    assert "Dashboard goal" in goal_titles
