"""Weekly Review Agent — generates a personalised weekly summary."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.llm import chat_completion
from models import CheckIn, Task, Goal

SYSTEM_PROMPT = """You are the Weekly Review Agent for Life OS.

Generate a brief, personalised weekly review. The user reads this Monday morning.

Structure:
1. "This week in your life" — 2-3 sentence overview
2. What went well — based on completed tasks, positive mood scores
3. What was tough — based on skipped tasks, low mood/energy days
4. One pattern to notice going into next week
5. One concrete suggestion for next week

Guidelines:
- Be warm but honest. Don't manufacture positivity.
- Use specific numbers from their data.
- Keep the whole review under 200 words.
- If data is sparse, acknowledge it and keep it short.
"""


async def run_weekly_review(user_id: str, db: AsyncSession) -> dict:
    """Generate a weekly review for the user.

    Returns the review text and raw stats.
    """
    from uuid import UUID
    uid = UUID(user_id)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # Check-ins this week
    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == uid, CheckIn.created_at >= week_ago)
        .order_by(CheckIn.checkin_date)
    )
    checkins = list(checkin_result.scalars().all())

    # Tasks this week
    task_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid, Task.created_at >= week_ago)
    )
    tasks = list(task_result.scalars().all())

    completed = [t for t in tasks if t.status == "completed"]
    pending = [t for t in tasks if t.status in ("pending", "in_progress")]
    deferred = [t for t in tasks if t.times_deferred > 0]

    # Goals
    goal_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == uid, Goal.status == "active")
    )
    goals = list(goal_result.scalars().all())

    # Compute stats
    mood_scores = [c.mood_score for c in checkins if c.mood_score]
    energy_scores = [c.energy_score for c in checkins if c.energy_score]
    sleep_hours = [c.sleep_hours for c in checkins if c.sleep_hours]

    avg_mood = round(sum(mood_scores) / len(mood_scores), 1) if mood_scores else None
    avg_energy = round(sum(energy_scores) / len(energy_scores), 1) if energy_scores else None
    avg_sleep = round(sum(sleep_hours) / len(sleep_hours), 1) if sleep_hours else None

    exercise_days = sum(1 for c in checkins if c.exercised)

    stats_block = f"""WEEKLY DATA:
- Check-ins logged: {len(checkins)}
- Tasks completed: {len(completed)} / {len(completed) + len(pending)} planned
- Tasks deferred: {len(deferred)}
- Average mood: {avg_mood or 'N/A'}/5
- Average energy: {avg_energy or 'N/A'}/5
- Average sleep: {avg_sleep or 'N/A'}h
- Exercise days: {exercise_days}
- Active goals: {len(goals)}
"""

    wins = []
    for c in checkins:
        if c.wins:
            wins.extend(c.wins)
    struggles = []
    for c in checkins:
        if c.struggles:
            struggles.extend(c.struggles)

    if wins:
        stats_block += f"\nUser-reported wins: {', '.join(wins[:5])}"
    if struggles:
        stats_block += f"\nUser-reported struggles: {', '.join(struggles[:5])}"

    messages = [
        {"role": "user", "content": f"{stats_block}\n\nGenerate the weekly review."},
    ]

    review_text = await chat_completion(SYSTEM_PROMPT, messages, max_tokens=600, user_id=user_id, db=db)

    return {
        "agent": "weekly_review",
        "review": review_text,
        "stats": {
            "checkins": len(checkins),
            "tasks_completed": len(completed),
            "tasks_pending": len(pending),
            "avg_mood": avg_mood,
            "avg_energy": avg_energy,
            "avg_sleep": avg_sleep,
            "exercise_days": exercise_days,
        },
    }
