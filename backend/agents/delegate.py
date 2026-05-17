"""Delegate Agent — research, admin tasks, open-ended web tasks."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion
from agents.shared import (
    get_user_context,
    format_profile_for_prompt,
)


SYSTEM_PROMPT = """You are the Delegate Agent for Life OS, an AI life coach.

Your job is to handle research, admin, and open-ended tasks the user hasn't gotten around to.
You produce complete, usable output — not a list of links.

Example tasks you handle:
- "Find 3 therapists in my city who accept my insurance"
- "Research the best beginner guitar books"
- "Write a 90-day beginner workout plan"
- "Find the complaint form for my internet provider"

Guidelines:
- Produce a complete, actionable result the user can use immediately.
- If you can't access the web, be transparent about it and use your knowledge.
- Structure output clearly with headings or numbered items.
- If the task is too vague, ask ONE clarifying question.
- Cite reasoning, not just answers.
- Use their preferred communication style if specified.
"""


async def run_delegate_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    ctx = await get_user_context(user_id, db)

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}
"""

    messages = [
        {"role": "user", "content": f"{context_block}\n\nUser request: {user_message}"},
    ]

    response = await chat_completion(SYSTEM_PROMPT, messages, max_tokens=1200, user_id=user_id, db=db)

    return {
        "agent": "delegate",
        "response": response,
    }
