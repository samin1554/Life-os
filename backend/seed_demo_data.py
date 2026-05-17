"""One-off demo data seeder — generates 30 days of realistic data for the test user.
Run: cd backend && source .venv/bin/activate && python seed_demo_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone, date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models import User, CheckIn, Task, Goal, UserPattern
from agents.pattern_learning import run_pattern_learning


async def get_or_create_test_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if user:
        print(f"Using existing user: {user.name} ({user.id})")
        return user

    user = User(
        clerk_id="demo_user",
        email="demo@lifeos.local",
        name="Demo User",
        timezone="UTC",
        onboarding_done=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    print(f"Created user: {user.name} ({user.id})")
    return user


async def seed_checkins(db: AsyncSession, user_id: UUID):
    print("Seeding check-ins...")
    base_date = date.today() - timedelta(days=30)

    for i in range(30):
        checkin_date = base_date + timedelta(days=i)

        # Skip some days randomly to make it realistic
        if random.random() < 0.15:
            continue

        # Correlated data: good sleep → better mood/energy
        sleep_hours = round(random.uniform(5.5, 8.5), 1)
        sleep_quality = min(5, max(1, int(sleep_hours - 3)))
        exercised = random.random() < 0.4

        # Mood/energy correlate with sleep
        base_mood = min(5, max(1, int(sleep_hours - 2)))
        mood = min(5, max(1, base_mood + random.randint(-1, 1)))
        energy = min(5, max(1, base_mood + random.randint(-1, 1)))
        stress = min(5, max(1, 6 - mood + random.randint(-1, 0)))
        focus = min(5, max(1, energy + random.randint(-1, 1)))

        wins = []
        struggles = []
        if mood >= 4:
            wins.append(random.choice(["Finished important task", "Good workout", "Quality time with friend", "Deep work session"]))
        if mood <= 2:
            struggles.append(random.choice(["Low energy day", "Procrastinated", "Poor sleep", "Overwhelmed"]))

        checkin = CheckIn(
            user_id=user_id,
            checkin_date=checkin_date,
            checkin_type="morning" if random.random() < 0.5 else "evening",
            mood_score=mood,
            energy_score=energy,
            stress_score=stress,
            focus_score=focus,
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            exercised=exercised,
            notes=f"Day {i+1} check-in" if random.random() < 0.3 else None,
            wins=wins if wins else None,
            struggles=struggles if struggles else None,
            tasks_planned=random.randint(3, 8) if random.random() < 0.5 else None,
            tasks_completed=random.randint(1, 6) if random.random() < 0.5 else None,
        )
        db.add(checkin)

    await db.commit()
    print("Check-ins seeded.")


async def seed_tasks(db: AsyncSession, user_id: UUID):
    print("Seeding tasks...")
    categories = ["work", "health", "personal", "finance", "learning"]
    statuses = ["pending", "in_progress", "completed"]
    weights = [0.4, 0.2, 0.4]

    base_date = datetime.now(timezone.utc) - timedelta(days=30)

    for i in range(25):
        status = random.choices(statuses, weights=weights)[0]
        created_at = base_date + timedelta(days=random.randint(0, 30))
        completed_at = None
        started_at = None
        actual_minutes = None
        times_deferred = 0

        if status == "completed":
            completed_at = created_at + timedelta(days=random.randint(0, 5))
            started_at = created_at + timedelta(hours=random.randint(1, 24))
            actual_minutes = random.randint(15, 180)
        elif status == "pending":
            times_deferred = random.choices([0, 1, 2, 3], weights=[0.5, 0.25, 0.15, 0.1])[0]

        estimated = random.choice([15, 30, 45, 60, 90, 120, 180])

        task = Task(
            user_id=user_id,
            title=random.choice([
                "Review project proposal", "Morning jog", "Read 20 pages",
                "Update budget spreadsheet", "Call dentist", "Write blog post",
                "Team standup prep", "Grocery shopping", "Meditate 10 min",
                "Email client follow-up", "Clean workspace", "Plan weekend trip",
                "Study Python async", "Meal prep", "Review investments",
                "Schedule doctor appointment", "Fix bug #442", "Water plants",
                "Journal entry", "Update resume", "Practice guitar",
                "Laundry", "Pay bills", "Organize photos", "Research new laptop",
            ]),
            description="Demo task for testing insights",
            category=random.choice(categories),
            status=status,
            priority=random.randint(1, 4),
            due_date=(created_at + timedelta(days=random.randint(1, 7))).date(),
            estimated_minutes=estimated,
            actual_minutes=actual_minutes,
            started_at=started_at,
            completed_at=completed_at,
            times_deferred=times_deferred,
            first_created_at=created_at,
            created_at=created_at,
        )
        db.add(task)

    await db.commit()
    print("Tasks seeded.")


async def seed_goals(db: AsyncSession, user_id: UUID):
    print("Seeding goals...")
    goals_data = [
        {"title": "Get fit", "domain": "health", "progress": 35},
        {"title": "Learn Spanish", "domain": "learning", "progress": 15},
        {"title": "Save $10K", "domain": "finance", "progress": 60},
        {"title": "Launch side project", "domain": "work", "progress": 10},
    ]

    for g in goals_data:
        goal = Goal(
            user_id=user_id,
            title=g["title"],
            description=f"Working toward {g['title'].lower()}",
            why="Personal growth and fulfillment",
            domain=g["domain"],
            timeframe="annual",
            status="active",
            progress_pct=g["progress"],
            last_action_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 14)),
            milestones={
                "m1": {"label": "Start", "done": True},
                "m2": {"label": "Quarter mark", "done": g["progress"] >= 25},
                "m3": {"label": "Halfway", "done": g["progress"] >= 50},
            },
        )
        db.add(goal)

    await db.commit()
    print("Goals seeded.")


async def run():
    async for db in get_db():
        user = await get_or_create_test_user(db)

        # Clear existing demo data for this user
        await db.execute(select(CheckIn).where(CheckIn.user_id == user.id))
        for model in [CheckIn, Task, Goal, UserPattern]:
            result = await db.execute(select(model).where(model.user_id == user.id))
            for row in result.scalars().all():
                await db.delete(row)
        await db.commit()
        print("Cleared old demo data.")

        await seed_checkins(db, user.id)
        await seed_tasks(db, user.id)
        await seed_goals(db, user.id)

        # Run pattern learning to populate user_patterns
        print("Running pattern learning...")
        await run_pattern_learning(str(user.id), db)
        print("Done! Pattern insights computed.")

        print("\n✅ Demo data seeded successfully.")
        print(f"   User: {user.name}")
        print(f"   Navigate to /insights and /weekly-review to see the data.")
        break


if __name__ == "__main__":
    asyncio.run(run())
