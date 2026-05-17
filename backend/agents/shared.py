"""Shared utilities for domain agents."""
import json
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from models import User, UserProfile, Task, CheckIn, Goal


async def get_user_context(user_id: str | UUID, db: AsyncSession) -> dict:
    """Fetch all relevant user context for agents.
    
    Returns a dict with:
    - profile: UserProfile or None
    - tasks: list of recent tasks (pending + in_progress + last 10 completed)
    - checkins: list of recent checkins (last 14 days)
    - goals: list of active goals
    - user: User object
    """
    uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id

    # User + profile
    user_result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.id == uid)
    )
    user = user_result.scalar_one_or_none()

    # Recent tasks
    task_result = await db.execute(
        select(Task)
        .where(Task.user_id == uid)
        .order_by(desc(Task.created_at))
        .limit(30)
    )
    tasks = list(task_result.scalars().all())

    # Recent checkins
    checkin_result = await db.execute(
        select(CheckIn)
        .where(CheckIn.user_id == uid)
        .order_by(desc(CheckIn.checkin_date))
        .limit(14)
    )
    checkins = list(checkin_result.scalars().all())

    # Active goals
    goal_result = await db.execute(
        select(Goal)
        .where(Goal.user_id == uid, Goal.status == "active")
        .order_by(desc(Goal.created_at))
        .limit(10)
    )
    goals = list(goal_result.scalars().all())

    if not user:
        return {
            "user": None,
            "profile": None,
            "tasks": [],
            "checkins": [],
            "goals": [],
        }

    return {
        "user": user,
        "profile": user.profile,
        "tasks": tasks,
        "checkins": checkins,
        "goals": goals,
    }


def format_tasks_for_prompt(tasks: list[Task]) -> str:
    """Format tasks into a concise string for LLM prompts."""
    if not tasks:
        return "No tasks on record."
    lines = []
    for t in tasks[:20]:
        due = f" (due {t.due_date})" if t.due_date else ""
        lines.append(f"- [{t.status}] {t.title}{due} (priority {t.priority}, est {t.estimated_minutes or '?'}m)")
    return "\n".join(lines)


def format_checkins_for_prompt(checkins: list[CheckIn]) -> str:
    """Format check-ins into a concise string for LLM prompts."""
    if not checkins:
        return "No check-ins on record."
    lines = []
    for c in checkins[:14]:
        scores = []
        if c.mood_score:
            scores.append(f"mood {c.mood_score}")
        if c.energy_score:
            scores.append(f"energy {c.energy_score}")
        if c.sleep_hours:
            scores.append(f"sleep {c.sleep_hours}h")
        if c.exercised is not None:
            scores.append("exercised" if c.exercised else "no exercise")
        line = f"- {c.checkin_date} ({c.checkin_type})"
        if scores:
            line += ": " + ", ".join(scores)
        lines.append(line)
    return "\n".join(lines)


def format_goals_for_prompt(goals: list[Goal]) -> str:
    """Format goals into a concise string for LLM prompts."""
    if not goals:
        return "No active goals."
    lines = []
    for g in goals:
        lines.append(f"- {g.title} ({g.domain or 'general'}, {g.progress_pct}%)")
    return "\n".join(lines)


def format_profile_for_prompt(profile: Optional[UserProfile]) -> str:
    """Format user profile into a concise string for LLM prompts."""
    if not profile:
        return "No profile data."
    parts = []
    if profile.occupation:
        parts.append(f"Occupation: {profile.occupation}")
    if profile.life_focus_areas:
        parts.append(f"Focus areas: {', '.join(profile.life_focus_areas)}")
    if profile.peak_energy_start and profile.peak_energy_end:
        parts.append(f"Peak energy: {profile.peak_energy_start}–{profile.peak_energy_end}")
    if profile.communication_style:
        parts.append(f"Communication style: {profile.communication_style}")
    if profile.coaching_tone:
        parts.append(f"Coaching tone: {profile.coaching_tone}")
    return "\n".join(parts) if parts else "Basic profile (no details yet)."


def extract_suggested_actions(response: str) -> tuple[str, list[dict]]:
    """Extract suggested_actions JSON block from the end of an agent response.

    Agents append a ```json block containing {"suggested_actions": [...]} at the
    end of their response. This function parses it out and returns:
    - The clean response text (with the JSON block stripped)
    - The list of suggested action dicts

    Returns:
        (clean_response, suggested_actions_list)
    """
    # Try to find ```json block containing suggested_actions
    pattern = r"```json\s*(\{[\s\S]*?\"suggested_actions\"[\s\S]*?\})\s*```"
    match = re.search(pattern, response)
    if match:
        try:
            data = json.loads(match.group(1))
            actions = data.get("suggested_actions", [])
            if isinstance(actions, list) and actions:
                clean = response[: match.start()].rstrip()
                return clean, actions
        except json.JSONDecodeError:
            pass

    # Try raw JSON object at the end (no code fence)
    pattern2 = r'(\{[^{}]*"suggested_actions"\s*:\s*\[[\s\S]*?\]\s*\})\s*$'
    match2 = re.search(pattern2, response)
    if match2:
        try:
            data = json.loads(match2.group(1))
            actions = data.get("suggested_actions", [])
            if isinstance(actions, list) and actions:
                clean = response[: match2.start()].rstrip()
                return clean, actions
        except json.JSONDecodeError:
            pass

    return response, []
