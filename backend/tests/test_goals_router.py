"""Tests for the goals router."""
import pytest
from datetime import datetime

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_goal(client, auth_headers):
    resp = await client.post("/goals", json={
        "title": "Learn guitar",
        "domain": "learning",
        "timeframe": "this_year",
        "why": "Always wanted to play music",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Learn guitar"
    assert data["domain"] == "learning"
    assert data["status"] == "active"
    assert data["progress_pct"] == 0


async def test_list_goals(client, auth_headers):
    await client.post("/goals", json={"title": "Run a 5K", "domain": "health"}, headers=auth_headers)
    await client.post("/goals", json={"title": "Read 12 books", "domain": "learning"}, headers=auth_headers)

    resp = await client.get("/goals", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["goals"]) >= 2


async def test_list_goals_filter_status(client, auth_headers):
    resp = await client.get("/goals?status=active", headers=auth_headers)
    assert resp.status_code == 200
    for goal in resp.json()["goals"]:
        assert goal["status"] == "active"


async def test_get_goal(client, auth_headers):
    create_resp = await client.post("/goals", json={"title": "Meditate daily"}, headers=auth_headers)
    goal_id = create_resp.json()["id"]

    resp = await client.get(f"/goals/{goal_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Meditate daily"


async def test_get_goal_not_found(client, auth_headers):
    resp = await client.get("/goals/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_goal(client, auth_headers):
    create_resp = await client.post("/goals", json={"title": "Save money"}, headers=auth_headers)
    goal_id = create_resp.json()["id"]

    resp = await client.patch(f"/goals/{goal_id}", json={
        "progress_pct": 50,
        "status": "active",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["progress_pct"] == 50


async def test_delete_goal(client, auth_headers):
    create_resp = await client.post("/goals", json={"title": "Temporary goal"}, headers=auth_headers)
    goal_id = create_resp.json()["id"]

    resp = await client.delete(f"/goals/{goal_id}", headers=auth_headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/goals/{goal_id}", headers=auth_headers)
    assert get_resp.status_code == 404


async def test_create_goal_validation_error(client, auth_headers):
    resp = await client.post("/goals", json={"title": ""}, headers=auth_headers)
    assert resp.status_code == 422
