"""Execution Agent — drafts content, researches, gets things done."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion
from core.config import get_settings
from agents.shared import (
    get_user_context,
    format_goals_for_prompt,
    format_profile_for_prompt,
)

settings = get_settings()

SYSTEM_PROMPT = """You are the Execution Agent for Life OS, an AI life coach.

Your job is to GET THINGS DONE for the user.
You draft emails, write documents, create outlines, summarize text, and help with research.

Guidelines:
- Produce ready-to-use output. The user should be able to copy-paste with minimal edits.
- Match their tone and context (professional vs casual).
- If drafting an email, include a subject line and full body.
- If summarizing, use bullet points.
- If researching, present findings clearly with sources if available.
- If you don't have enough context, ask clarifying questions (max 2).
- Use their preferred communication style if specified.
"""


async def run_execution_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    """Run the Execution Agent.
    
    Returns:
        {
            "agent": "execution",
            "response": str,
            "output_type": str,  # e.g. "email", "summary", "research", "draft"
        }
    """
    ctx = await get_user_context(user_id, db)

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}

ACTIVE GOALS:
{format_goals_for_prompt(ctx['goals'])}
"""

    # TODO: Tavily web search integration when API key is configured
    # For MVP, skip web search and rely on LLM knowledge
    research_context = ""
    if any(kw in user_message.lower() for kw in ("research", "look up", "find", "search", "what is", "how to")):
        research_context = "\n[Note: Web search is not enabled for this request. Using internal knowledge.]"

    messages = [
        {"role": "user", "content": f"{context_block}{research_context}\n\nUser request: {user_message}"},
    ]

    response = await chat_completion(SYSTEM_PROMPT, messages, max_tokens=1200, user_id=user_id, db=db)

    # Simple heuristic for output type
    output_type = "draft"
    msg_lower = user_message.lower()
    if any(kw in msg_lower for kw in ("email", "write to", "draft message")):
        output_type = "email"
    elif any(kw in msg_lower for kw in ("summarize", "summary", "tl;dr")):
        output_type = "summary"
    elif any(kw in msg_lower for kw in ("research", "look up", "find", "search")):
        output_type = "research"

    return {
        "agent": "execution",
        "response": response,
        "output_type": output_type,
    }
