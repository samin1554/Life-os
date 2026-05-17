"""Goals Agent — long-term goal tracking, drift alerts, milestone management."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion
from agents.shared import (
    get_user_context,
    format_goals_for_prompt,
    format_tasks_for_prompt,
    format_profile_for_prompt,
    extract_suggested_actions,
)
from agents.registry import get_collaboration_prompt


SYSTEM_PROMPT = """You are the Goals Agent for Life OS, an AI life coach.

Your job is to help the user set, track, and achieve their long-term goals.
You have access to their active goals, recent tasks, and profile.

Guidelines:
- Help break large goals into concrete weekly milestones.
- Flag drift: if a goal hasn't had progress in 2+ weeks, surface it gently.
- Connect daily tasks to bigger goals so the user sees the link.
- Celebrate real progress — don't manufacture encouragement.
- If they mention a new goal, help them define it clearly (title, why, timeframe).
- Suggest ONE small step they could take this week toward a stalled goal.
- Use their preferred coaching tone if specified.
"""


async def run_goals_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    ctx = await get_user_context(user_id, db)

    goals = ctx["goals"]
    pending_tasks = [t for t in ctx["tasks"] if t.status in ("pending", "in_progress")]

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}

ACTIVE GOALS ({len(goals)}):
{format_goals_for_prompt(goals)}

PENDING TASKS ({len(pending_tasks)}):
{format_tasks_for_prompt(pending_tasks)}
"""

    full_prompt = SYSTEM_PROMPT + get_collaboration_prompt("goals")

    messages = [
        {"role": "user", "content": f"{context_block}\n\nUser message: {user_message}"},
    ]

    response = await chat_completion(full_prompt, messages, max_tokens=1000, user_id=user_id, db=db)
    clean_response, suggestions = extract_suggested_actions(response)

    return {
        "agent": "goals",
        "response": clean_response,
        "goal_count": len(goals),
        "suggested_actions": suggestions,
    }
