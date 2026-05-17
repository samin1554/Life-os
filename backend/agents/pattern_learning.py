"""Pattern Learning Agent — nightly background job that analyses user behaviour."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import User, CheckIn, Task, UserPattern
from core.memory import save_memory

logger = logging.getLogger(__name__)


async def run_pattern_learning(user_id: str, db: AsyncSession) -> dict:
    """Analyse last 7 days of data and update the user's behavioural model.

    Updates:
    - user_patterns table (structured metrics)
    - Mem0 memories tagged pattern_learned
    """
    from uuid import UUID
    uid = UUID(user_id)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # --- Fetch raw data ---

    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == uid, CheckIn.created_at >= week_ago)
        .order_by(CheckIn.checkin_date)
    )
    checkins = list(checkin_result.scalars().all())

    task_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid, Task.created_at >= week_ago)
    )
    tasks = list(task_result.scalars().all())

    # --- Compute metrics ---

    # Time estimation bias
    timed_tasks = [t for t in tasks if t.estimated_minutes and t.actual_minutes and t.actual_minutes > 0]
    time_bias = None
    if len(timed_tasks) >= 3:
        ratios = [t.actual_minutes / t.estimated_minutes for t in timed_tasks]
        time_bias = sum(ratios) / len(ratios)

    # Completion rate
    completed = [t for t in tasks if t.status == "completed"]
    all_actionable = [t for t in tasks if t.status in ("completed", "pending", "in_progress")]
    completion_rate = len(completed) / len(all_actionable) if all_actionable else None

    # Avoidance categories
    deferred = [t for t in tasks if t.times_deferred >= 3 and t.category]
    avoidance_cats = list({t.category for t in deferred}) if deferred else None

    # Average deferral
    deferred_tasks = [t for t in tasks if t.times_deferred > 0]
    avg_deferral = sum(t.times_deferred for t in deferred_tasks) / len(deferred_tasks) if deferred_tasks else None

    # Mood-sleep correlation (simple)
    mood_sleep_pairs = [
        (c.mood_score, c.sleep_hours)
        for c in checkins
        if c.mood_score is not None and c.sleep_hours is not None
    ]
    mood_sleep_corr = _simple_correlation(mood_sleep_pairs) if len(mood_sleep_pairs) >= 3 else None

    # Mood-exercise correlation
    mood_exercise_pairs = [
        (c.mood_score, 1.0 if c.exercised else 0.0)
        for c in checkins
        if c.mood_score is not None and c.exercised is not None
    ]
    mood_exercise_corr = _simple_correlation(mood_exercise_pairs) if len(mood_exercise_pairs) >= 3 else None

    # Check-in streak
    today = now.date()
    streak = 0
    check_date = today
    checkin_dates = {c.checkin_date for c in checkins}
    # Extend with older data
    older_result = await db.execute(
        select(CheckIn.checkin_date)
        .where(CheckIn.user_id == uid)
        .distinct()
        .order_by(CheckIn.checkin_date.desc())
        .limit(365)
    )
    all_dates = {row[0] for row in older_result.all()}
    while check_date in all_dates:
        streak += 1
        check_date -= timedelta(days=1)

    # --- Upsert user_patterns ---

    pattern_result = await db.execute(
        select(UserPattern).where(UserPattern.user_id == uid)
    )
    pattern = pattern_result.scalar_one_or_none()

    if not pattern:
        pattern = UserPattern(user_id=uid)
        db.add(pattern)

    if time_bias is not None:
        pattern.time_estimation_bias = round(time_bias, 2)
    if completion_rate is not None:
        pattern.avg_completion_rate_7d = round(completion_rate, 2)
    if avoidance_cats is not None:
        pattern.top_avoidance_categories = avoidance_cats
    if avg_deferral is not None:
        pattern.avg_deferral_count = round(avg_deferral, 1)
    if mood_sleep_corr is not None:
        pattern.mood_sleep_correlation = round(mood_sleep_corr, 2)
    if mood_exercise_corr is not None:
        pattern.mood_exercise_correlation = round(mood_exercise_corr, 2)
    pattern.checkin_streak = streak
    if streak > (pattern.longest_checkin_streak or 0):
        pattern.longest_checkin_streak = streak
    pattern.last_computed_at = now

    await db.commit()

    # --- Save insights to semantic memory ---

    insights = []
    if time_bias is not None and abs(time_bias - 1.0) > 0.15:
        direction = "underestimates" if time_bias > 1.0 else "overestimates"
        pct = abs(round((time_bias - 1.0) * 100))
        insight = f"User typically {direction} task duration by {pct}%"
        insights.append(insight)

    if completion_rate is not None:
        insight = f"User's 7-day task completion rate is {round(completion_rate * 100)}%"
        insights.append(insight)

    if mood_sleep_corr is not None and abs(mood_sleep_corr) > 0.3:
        strength = "strong" if abs(mood_sleep_corr) > 0.6 else "moderate"
        insight = f"User shows {strength} correlation between sleep and mood"
        insights.append(insight)

    for insight in insights:
        try:
            save_memory(
                user_id=user_id,
                content=insight,
                metadata={
                    "source_actor": "pattern_learning_agent",
                    "confidence": 0.7,
                    "category": "pattern_learned",
                },
            )
        except Exception:
            logger.warning("Failed to save pattern memory: %s", insight)

    return {
        "user_id": user_id,
        "checkins_analysed": len(checkins),
        "tasks_analysed": len(tasks),
        "insights": insights,
        "time_estimation_bias": time_bias,
        "completion_rate": completion_rate,
        "streak": streak,
    }


def _simple_correlation(pairs: list[tuple[float, float]]) -> float:
    """Pearson correlation for small datasets."""
    n = len(pairs)
    if n < 2:
        return 0.0
    xs, ys = zip(*pairs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if den_x * den_y == 0:
        return 0.0
    return num / (den_x * den_y)
