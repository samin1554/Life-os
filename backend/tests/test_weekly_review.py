"""Tests for the Weekly Review Agent."""
import pytest
import uuid
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

from models import User, CheckIn, Task, Goal

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_weekly_review_generates_review(db_session):
    from agents.weekly_review import run_weekly_review

    user = User(
        email=f"review_{uuid.uuid4().hex[:8]}@test.com",
        name="Review User",
        clerk_id=f"clerk_review_{uuid.uuid4().hex[:8]}",
        onboarding_done=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    now = datetime.now(timezone.utc)
    for i in range(4):
        db_session.add(CheckIn(
            user_id=user.id,
            checkin_type="morning",
            checkin_date=date.today() - timedelta(days=i),
            mood_score=4,
            energy_score=3,
            sleep_hours=7.5,
            exercised=i % 2 == 0,
        ))
        db_session.add(Task(
            user_id=user.id,
            title=f"Review task {i}",
            status="completed",
            completed_at=now - timedelta(days=i),
        ))
    db_session.add(Goal(
        user_id=user.id,
        title="Test goal",
        status="active",
    ))
    await db_session.commit()

    with patch("agents.weekly_review.chat_completion", new_callable=AsyncMock,
               return_value="Great week! You completed 4 tasks and maintained solid energy."):
        result = await run_weekly_review(str(user.id), db_session)

    assert result["agent"] == "weekly_review"
    assert isinstance(result["review"], str)
    assert len(result["review"]) > 0
    assert result["stats"]["tasks_completed"] >= 4
    assert result["stats"]["checkins"] >= 4
    assert result["stats"]["avg_mood"] is not None


async def test_weekly_review_no_data(db_session):
    from agents.weekly_review import run_weekly_review

    user = User(
        email=f"empty_review_{uuid.uuid4().hex[:8]}@test.com",
        name="Empty Review User",
        clerk_id=f"clerk_er_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    with patch("agents.weekly_review.chat_completion", new_callable=AsyncMock,
               return_value="Not much data yet. Keep checking in!"):
        result = await run_weekly_review(str(user.id), db_session)

    assert result["stats"]["checkins"] == 0
    assert result["stats"]["tasks_completed"] == 0
    assert result["stats"]["avg_mood"] is None
