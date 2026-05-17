"""Tests for CheckIn router."""
import pytest
from datetime import date, datetime, timezone

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_checkin(client, auth_headers):
    resp = await client.post(
        "/checkins",
        json={
            "checkin_type": "morning",
            "checkin_date": str(date.today()),
            "mood_score": 4,
            "energy_score": 3,
            "sleep_hours": 7.5,
            "exercised": True,
            "notes": "Feeling good",
            "wins": ["Got up early"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["checkin_type"] == "morning"
    assert data["mood_score"] == 4
    assert data["energy_score"] == 3
    assert data["exercised"] is True
    assert data["notes"] == "Feeling good"
    assert data["wins"] == ["Got up early"]
    assert "id" in data


async def test_list_checkins(client, auth_headers, db_session):
    from models import CheckIn

    c1 = CheckIn(user_id=client.user_id, checkin_type="morning", checkin_date=date.today())
    c2 = CheckIn(user_id=client.user_id, checkin_type="evening", checkin_date=date.today())
    db_session.add_all([c1, c2])
    await db_session.commit()

    resp = await client.get("/checkins", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["checkins"]) >= 2


async def test_list_checkins_filter_type(client, auth_headers, db_session):
    from models import CheckIn

    c = CheckIn(user_id=client.user_id, checkin_type="evening", checkin_date=date.today())
    db_session.add(c)
    await db_session.commit()

    resp = await client.get("/checkins?checkin_type=evening", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for checkin in data["checkins"]:
        assert checkin["checkin_type"] == "evening"


async def test_get_checkin(client, auth_headers, db_session):
    from models import CheckIn

    c = CheckIn(user_id=client.user_id, checkin_type="midday", checkin_date=date.today())
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await client.get(f"/checkins/{c.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["checkin_type"] == "midday"


async def test_get_checkin_not_found(client, auth_headers):
    import uuid
    resp = await client.get(f"/checkins/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


async def test_update_checkin(client, auth_headers, db_session):
    from models import CheckIn

    c = CheckIn(user_id=client.user_id, checkin_type="morning", checkin_date=date.today())
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await client.patch(
        f"/checkins/{c.id}",
        json={"mood_score": 5, "notes": "Updated note"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mood_score"] == 5
    assert data["notes"] == "Updated note"


async def test_delete_checkin(client, auth_headers, db_session):
    from models import CheckIn

    c = CheckIn(user_id=client.user_id, checkin_type="morning", checkin_date=date.today())
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    resp = await client.delete(f"/checkins/{c.id}", headers=auth_headers)
    assert resp.status_code == 204

    resp2 = await client.get(f"/checkins/{c.id}", headers=auth_headers)
    assert resp2.status_code == 404


async def test_create_checkin_validation_error(client, auth_headers):
    resp = await client.post("/checkins", json={"checkin_type": "invalid", "checkin_date": "bad"}, headers=auth_headers)
    assert resp.status_code == 422
