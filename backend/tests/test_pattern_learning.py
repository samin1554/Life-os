"""Tests for the Pattern Learning Agent."""
import pytest
import uuid
from datetime import date, datetime, timezone, timedelta

from models import User, CheckIn, Task, UserPattern

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_pattern_learning_creates_patterns(db_session):
    from agents.pattern_learning import run_pattern_learning

    user = User(
        email=f"pattern_{uuid.uuid4().hex[:8]}@test.com",
        name="Pattern User",
        clerk_id=f"clerk_pattern_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    now = datetime.now(timezone.utc)
    for i in range(5):
        db_session.add(CheckIn(
            user_id=user.id,
            checkin_type="morning",
            checkin_date=date.today() - timedelta(days=i),
            mood_score=3 + (i % 2),
            energy_score=3,
            sleep_hours=6.5 + (i * 0.3),
        ))
        db_session.add(Task(
            user_id=user.id,
            title=f"Task {i}",
            status="completed" if i < 3 else "pending",
            estimated_minutes=30,
            actual_minutes=40 + i * 5,
            completed_at=now - timedelta(days=i) if i < 3 else None,
        ))
    await db_session.commit()

    result = await run_pattern_learning(str(user.id), db_session)

    assert result["checkins_analysed"] >= 5
    assert result["tasks_analysed"] >= 5
    assert result["time_estimation_bias"] is not None
    assert result["time_estimation_bias"] > 1.0
    assert result["completion_rate"] is not None

    # Verify user_patterns row was created
    from sqlalchemy import select
    pat_result = await db_session.execute(
        select(UserPattern).where(UserPattern.user_id == user.id)
    )
    pattern = pat_result.scalar_one_or_none()
    assert pattern is not None
    assert pattern.time_estimation_bias > 1.0
    assert pattern.last_computed_at is not None


async def test_pattern_learning_no_data(db_session):
    from agents.pattern_learning import run_pattern_learning

    user = User(
        email=f"empty_{uuid.uuid4().hex[:8]}@test.com",
        name="Empty User",
        clerk_id=f"clerk_empty_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    result = await run_pattern_learning(str(user.id), db_session)

    assert result["checkins_analysed"] == 0
    assert result["tasks_analysed"] == 0
    assert result["time_estimation_bias"] is None
    assert result["completion_rate"] is None
    assert result["streak"] == 0


async def test_simple_correlation():
    from agents.pattern_learning import _simple_correlation

    perfect = [(1, 1), (2, 2), (3, 3)]
    assert abs(_simple_correlation(perfect) - 1.0) < 0.01

    inverse = [(1, 3), (2, 2), (3, 1)]
    assert abs(_simple_correlation(inverse) - (-1.0)) < 0.01

    no_data = [(1, 1)]
    assert _simple_correlation(no_data) == 0.0
