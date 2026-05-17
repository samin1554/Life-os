"""Focus Agent — task planning, prioritization, daily focus."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion
from agents.shared import (
    get_user_context,
    format_tasks_for_prompt,
    format_goals_for_prompt,
    format_profile_for_prompt,
    extract_suggested_actions,
)
from agents.registry import get_collaboration_prompt


SYSTEM_PROMPT = """You are the Focus Agent for Life OS, an AI life coach.

Your job is to help the user plan, prioritize, and stay focused.
You have access to their tasks, goals, and profile (energy patterns, focus areas).

Guidelines:
- Be concise and actionable. Prefer bullet points.
- Reference their actual tasks and goals when relevant.
- Respect their peak energy windows from their profile.
- Suggest 1-3 concrete next actions, not vague advice.
- If they ask "what should I do now?", suggest the highest-impact task that fits their energy.
- If they seem scattered, help them narrow to ONE thing.
- Use their preferred coaching tone if specified in their profile.
"""


async def run_focus_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    """Run the Focus Agent.
    
    Returns:
        {
            "agent": "focus",
            "response": str,
            "suggested_tasks": list[dict],  # Optional task suggestions
        }
    """
    ctx = await get_user_context(user_id, db)

    pending = [t for t in ctx["tasks"] if t.status in ("pending", "in_progress")]
    completed_today = [t for t in ctx["tasks"] if t.status == "completed"]

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}

ACTIVE GOALS:
{format_goals_for_prompt(ctx['goals'])}

PENDING/IN-PROGRESS TASKS ({len(pending)}):
{format_tasks_for_prompt(pending)}

COMPLETED TODAY ({len(completed_today)}):
{format_tasks_for_prompt(completed_today)}
"""

    full_prompt = SYSTEM_PROMPT + get_collaboration_prompt("focus")

    messages = [
        {"role": "user", "content": f"{context_block}\n\nUser message: {user_message}"},
    ]

    response = await chat_completion(full_prompt, messages, max_tokens=1000, user_id=user_id, db=db)
    clean_response, suggestions = extract_suggested_actions(response)

    return {
        "agent": "focus",
        "response": clean_response,
        "pending_count": len(pending),
        "suggested_actions": suggestions,
    }
