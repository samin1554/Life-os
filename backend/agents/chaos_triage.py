"""Chaos Triage Agent — helps when user is overwhelmed."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion, extract_structured
from agents.shared import (
    get_user_context,
    format_tasks_for_prompt,
    format_goals_for_prompt,
    format_profile_for_prompt,
)


SYSTEM_PROMPT = """You are the Chaos Triage Agent for Life OS, an AI life coach.

Your job is to help the user when they feel overwhelmed.
You help them:
1. Brain-dump everything on their mind
2. Distinguish urgent vs important
3. Pick 1-3 things to do next (not everything)
4. Create a simple, achievable plan

Guidelines:
- Be calm, reassuring, and non-judgmental.
- DO NOT tell them to "just do it" or shame them.
- Acknowledge the overwhelm first ("That sounds like a lot").
- Help them externalize the chaos — get it out of their head.
- Use the Eisenhower matrix if helpful: urgent/important.
- End with ONE concrete next step they can take in the next 15 minutes.
- Use their preferred coaching tone if specified.
"""


async def run_chaos_triage_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    """Run the Chaos Triage Agent.
    
    Returns:
        {
            "agent": "chaos_triage",
            "response": str,
            "extracted_items": list[str],  # Brain-dump items
            "priority_action": str,
        }
    """
    ctx = await get_user_context(user_id, db)

    pending = [t for t in ctx["tasks"] if t.status in ("pending", "in_progress")]

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}

ACTIVE GOALS:
{format_goals_for_prompt(ctx['goals'])}

EXISTING PENDING TASKS ({len(pending)}):
{format_tasks_for_prompt(pending)}
"""

    messages = [
        {"role": "user", "content": f"{context_block}\n\nUser message: {user_message}"},
    ]

    response = await chat_completion(SYSTEM_PROMPT, messages, max_tokens=900, user_id=user_id, db=db)

    # Try to extract structured items from the conversation
    extract_prompt = """From the user's message, extract a JSON list of items they mentioned feeling overwhelmed by.
If they listed things, return each as a string. If not, return an empty list.

Respond with valid JSON: {"items": ["item 1", "item 2", ...]}"""
    extract_messages = [{"role": "user", "content": user_message}]
    try:
        extracted = await extract_structured(extract_prompt, extract_messages, max_tokens=512, user_id=user_id, db=db)
        extracted_items = extracted.get("items", [])
    except Exception:
        extracted_items = []

    return {
        "agent": "chaos_triage",
        "response": response,
        "extracted_items": extracted_items if isinstance(extracted_items, list) else [],
        "pending_count": len(pending),
    }
