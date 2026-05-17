"""Tests for Task router."""
import pytest
from datetime import date, datetime, timezone

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_task(client, auth_headers):
    resp = await client.post(
        "/tasks",
        json={"title": "Test task", "description": "A test", "category": "work", "priority": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test task"
    assert data["status"] == "pending"
    assert data["priority"] == 3
    assert data["category"] == "work"
    assert "id" in data


async def test_list_tasks(client, auth_headers, db_session):
    from models import Task

    t1 = Task(user_id=client.user_id, title="T1", status="pending")
    t2 = Task(user_id=client.user_id, title="T2", status="completed")
    db_session.add_all([t1, t2])
    await db_session.commit()

    resp = await client.get("/tasks", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["tasks"]) >= 2


async def test_list_tasks_filter_status(client, auth_headers, db_session):
    from models import Task

    t = Task(user_id=client.user_id, title="Pending only", status="pending")
    db_session.add(t)
    await db_session.commit()

    resp = await client.get("/tasks?status=pending", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for task in data["tasks"]:
        assert task["status"] == "pending"


async def test_get_task(client, auth_headers, db_session):
    from models import Task

    t = Task(user_id=client.user_id, title="Single", status="pending")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)

    resp = await client.get(f"/tasks/{t.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Single"


async def test_get_task_not_found(client, auth_headers):
    import uuid
    resp = await client.get(f"/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_task(client, auth_headers, db_session):
    from models import Task

    t = Task(user_id=client.user_id, title="Old", status="pending")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)

    resp = await client.patch(
        f"/tasks/{t.id}",
        json={"title": "New", "status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New"
    assert data["status"] == "in_progress"


async def test_delete_task(client, auth_headers, db_session):
    from models import Task

    t = Task(user_id=client.user_id, title="Delete me", status="pending")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)

    resp = await client.delete(f"/tasks/{t.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/tasks/{t.id}", headers=auth_headers)
    assert resp2.status_code == 404


async def test_create_task_validation_error(client, auth_headers):
    resp = await client.post("/tasks", json={"title": ""}, headers=auth_headers)
    assert resp.status_code == 422
