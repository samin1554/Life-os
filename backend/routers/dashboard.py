"""Dashboard route — aggregated view for the frontend."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from core.database import get_db
from core.security import get_current_user
from models import User, Task, CheckIn, Goal, AgentInteraction, UserPattern, UserApiKey
from agents.runner import AGENT_DISPLAY_NAMES
from agents.weekly_review import run_weekly_review

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everything the frontend needs for the main dashboard in one call."""
    uid = current_user.id
    today = date.today()
    week_ago = today - timedelta(days=7)

    # Today's tasks (pending + in_progress, ordered by priority)
    task_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid, Task.status.in_(["pending", "in_progress"]))
        .order_by(Task.priority, Task.created_at)
        .limit(20)
    )
    pending_tasks = task_result.scalars().all()

    # Completed tasks this week
    completed_result = await db.execute(
        select(func.count())
        .select_from(Task)
        .where(
            Task.user_id == uid,
            Task.status == "completed",
            Task.completed_at >= today - timedelta(days=7),
        )
    )
    completed_this_week = completed_result.scalar() or 0

    # Today's check-in status
    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == uid, CheckIn.checkin_date == today)
        .order_by(desc(CheckIn.created_at))
    )
    todays_checkins = checkin_result.scalars().all()
    checkin_done = len(todays_checkins) > 0

    latest_checkin = todays_checkins[0] if todays_checkins else None

    # Check-in streak
    streak = 0
    streak_date = today
    while True:
        streak_result = await db.execute(
            select(func.count())
            .select_from(CheckIn)
            .where(CheckIn.user_id == uid, CheckIn.checkin_date == streak_date)
        )
        if streak_result.scalar() > 0:
            streak += 1
            streak_date -= timedelta(days=1)
        else:
            break
        if streak > 365:
            break

    # Active goals with drift detection
    goal_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == uid, Goal.status == "active")
        .order_by(desc(Goal.created_at))
        .limit(10)
    )
    goals = goal_result.scalars().all()

    goal_summaries = []
    for g in goals:
        drift = False
        if g.last_action_at:
            drift = (today - g.last_action_at.date()).days >= 14
        elif g.created_at:
            drift = (today - g.created_at.date()).days >= 14

        goal_summaries.append({
            "id": str(g.id),
            "title": g.title,
            "domain": g.domain,
            "progress_pct": g.progress_pct,
            "drift_alert": drift,
        })

    # 7-day mood/energy averages
    avg_result = await db.execute(
        select(
            func.avg(CheckIn.mood_score),
            func.avg(CheckIn.energy_score),
            func.avg(CheckIn.sleep_hours),
        )
        .where(CheckIn.user_id == uid, CheckIn.checkin_date >= week_ago)
    )
    avgs = avg_result.first()

    # Agent status cards
    agent_cards = []
    for name, display in AGENT_DISPLAY_NAMES.items():
        latest_result = await db.execute(
            select(AgentInteraction)
            .where(
                AgentInteraction.user_id == uid,
                AgentInteraction.agent_name == name,
            )
            .order_by(desc(AgentInteraction.created_at))
            .limit(1)
        )
        latest = latest_result.scalar_one_or_none()

        runs_today_result = await db.execute(
            select(func.count())
            .select_from(AgentInteraction)
            .where(
                AgentInteraction.user_id == uid,
                AgentInteraction.agent_name == name,
                func.date(AgentInteraction.created_at) == today,
            )
        )
        runs_today = runs_today_result.scalar() or 0

        agent_cards.append({
            "name": name,
            "display_name": display,
            "status": "running" if latest and latest.status == "running" else "idle",
            "last_run_at": str(latest.completed_at or latest.started_at) if latest else None,
            "last_output_summary": latest.output_summary if latest else None,
            "runs_today": runs_today,
        })

    # Check if user has any LLM API keys configured
    api_key_result = await db.execute(
        select(func.count()).select_from(UserApiKey)
        .where(UserApiKey.user_id == uid, UserApiKey.provider.notin_(["tavily"]))
    )
    has_api_keys = (api_key_result.scalar() or 0) > 0

    return {
        "today": {
            "date": str(today),
            "pending_tasks": len(pending_tasks),
            "checkin_done": checkin_done,
            "energy_level": _energy_label(latest_checkin.energy_score if latest_checkin else None),
        },
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "due_date": str(t.due_date) if t.due_date else None,
                "times_deferred": t.times_deferred,
            }
            for t in pending_tasks[:10]
        ],
        "streak": streak,
        "completed_this_week": completed_this_week,
        "goals": goal_summaries,
        "averages": {
            "mood": round(float(avgs[0]), 1) if avgs[0] else None,
            "energy": round(float(avgs[1]), 1) if avgs[1] else None,
            "sleep": round(float(avgs[2]), 1) if avgs[2] else None,
        },
        "onboarding_done": current_user.onboarding_done,
        "has_api_keys": has_api_keys,
        "api_key_disclaimer_dismissed": current_user.api_key_disclaimer_dismissed,
        "agents": agent_cards,
    }


def _energy_label(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score >= 4:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated analytics data for the Insights page charts."""
    uid = current_user.id
    today = date.today()
    week_ago = today - timedelta(days=7)

    # --- Time-series: all daily check-in scores ---
    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == uid)
        .order_by(CheckIn.checkin_date)
    )
    checkins = list(checkin_result.scalars().all())

    daily_vitals = {}
    for c in checkins:
        d = str(c.checkin_date)
        if d not in daily_vitals:
            daily_vitals[d] = {"mood": None, "energy": None, "sleep": None, "exercise": False}
        # Take the latest check-in of the day for each metric
        if c.mood_score is not None:
            daily_vitals[d]["mood"] = c.mood_score
        if c.energy_score is not None:
            daily_vitals[d]["energy"] = c.energy_score
        if c.sleep_hours is not None:
            daily_vitals[d]["sleep"] = round(c.sleep_hours, 1)
        if c.exercised:
            daily_vitals[d]["exercise"] = True

    vitals_series = [
        {"date": d, "mood": v["mood"], "energy": v["energy"], "sleep": v["sleep"], "exercise": v["exercise"]}
        for d, v in sorted(daily_vitals.items())
    ]

    # --- Task analytics (all time) ---
    task_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid)
    )
    tasks = list(task_result.scalars().all())

    # Daily completion counts
    daily_tasks = {}
    for t in tasks:
        created_d = t.created_at.date() if t.created_at else today
        d_str = str(created_d)
        if d_str not in daily_tasks:
            daily_tasks[d_str] = {"created": 0, "completed": 0}
        daily_tasks[d_str]["created"] += 1
        if t.status == "completed" and t.completed_at and t.completed_at.date() == created_d:
            daily_tasks[d_str]["completed"] += 1

    task_velocity = [
        {"date": d, "created": v["created"], "completed": v["completed"]}
        for d, v in sorted(daily_tasks.items())
    ]

    # Category breakdown
    category_counts = {}
    for t in tasks:
        cat = t.category or "uncategorized"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    category_breakdown = [
        {"category": cat, "count": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
    ]

    # --- Goals ---
    goal_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == uid, Goal.status == "active")
        .order_by(desc(Goal.created_at))
    )
    goals = list(goal_result.scalars().all())

    goal_progress = [
        {"id": str(g.id), "title": g.title, "domain": g.domain, "progress_pct": g.progress_pct}
        for g in goals
    ]

    # --- Patterns from user_patterns table ---
    pattern_result = await db.execute(
        select(UserPattern).where(UserPattern.user_id == uid)
    )
    pattern = pattern_result.scalar_one_or_none()

    pattern_insights = {}
    if pattern:
        pattern_insights = {
            "time_estimation_bias": pattern.time_estimation_bias,
            "avg_completion_rate_7d": pattern.avg_completion_rate_7d,
            "top_avoidance_categories": pattern.top_avoidance_categories or [],
            "avg_deferral_count": pattern.avg_deferral_count,
            "mood_sleep_correlation": pattern.mood_sleep_correlation,
            "mood_exercise_correlation": pattern.mood_exercise_correlation,
            "checkin_streak": pattern.checkin_streak,
            "longest_checkin_streak": pattern.longest_checkin_streak,
            "last_computed_at": str(pattern.last_computed_at) if pattern.last_computed_at else None,
        }

    # --- Recent weekly averages ---
    week_checkins = [c for c in checkins if c.checkin_date >= week_ago]
    mood_scores = [c.mood_score for c in week_checkins if c.mood_score is not None]
    energy_scores = [c.energy_score for c in week_checkins if c.energy_score is not None]
    sleep_hours = [c.sleep_hours for c in week_checkins if c.sleep_hours is not None]

    return {
        "vitals_series": vitals_series,
        "task_velocity": task_velocity,
        "category_breakdown": category_breakdown,
        "goal_progress": goal_progress,
        "pattern_insights": pattern_insights,
        "weekly_averages": {
            "mood": round(sum(mood_scores) / len(mood_scores), 1) if mood_scores else None,
            "energy": round(sum(energy_scores) / len(energy_scores), 1) if energy_scores else None,
            "sleep": round(sum(sleep_hours) / len(sleep_hours), 1) if sleep_hours else None,
        },
    }


@router.get("/weekly-review")
async def get_weekly_review(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return the current weekly review."""
    result = await run_weekly_review(str(current_user.id), db)
    return {
        "review": result.get("review", ""),
        "stats": result.get("stats", {}),
        "generated_at": str(date.today()),
    }


@router.post("/weekly-review")
async def regenerate_weekly_review(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Force regeneration of the weekly review."""
    result = await run_weekly_review(str(current_user.id), db)
    return {
        "review": result.get("review", ""),
        "stats": result.get("stats", {}),
        "generated_at": str(date.today()),
    }
