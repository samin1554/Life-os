"""Synthesis Agent — combines outputs from multiple agents into a coherent response."""
from core.llm import chat_completion


SYSTEM_PROMPT = """You are the Synthesis Agent for Life OS, an AI life coach.

Your job is to take outputs from multiple specialist agents and weave them into ONE coherent, natural-sounding response to the user.

Guidelines:
- Speak in first person as Life OS ("I", "me", "my").
- Do NOT mention "agents" or "the focus agent said" — integrate seamlessly.
- Prioritize clarity and actionability.
- If agents gave conflicting advice, reconcile it gracefully.
- Keep the response concise (under 300 words ideally).
- Match the user's energy and context. If they're overwhelmed, be gentle. If they're ready to act, be direct.
- End with ONE clear next step or question.
"""


async def run_synthesis_agent(
    user_message: str,
    agent_outputs: list[dict],
    user_name: str = "",
    user_id=None,
    db=None,
) -> dict:
    """Run the Synthesis Agent.
    
    Args:
        user_message: The original user message.
        agent_outputs: List of dicts from domain agents, each with at least "agent" and "response".
        user_name: Optional user name for personalization.
    
    Returns:
        {
            "agent": "synthesis",
            "response": str,
            "sources": list[str],  # Which agents contributed
        }
    """
    sources = [out["agent"] for out in agent_outputs if out.get("response")]

    agent_sections = []
    for out in agent_outputs:
        agent_name = out.get("agent", "unknown")
        response = out.get("response", "")
        if response:
            agent_sections.append(f"--- {agent_name.upper()} ---\n{response}")

    joined_sections = "\n\n".join(agent_sections)
    context_block = f"""USER MESSAGE: {user_message}

AGENT OUTPUTS:
{joined_sections}
"""

    messages = [
        {"role": "user", "content": context_block},
    ]

    response = await chat_completion(SYSTEM_PROMPT, messages, max_tokens=1000, user_id=user_id, db=db)

    return {
        "agent": "synthesis",
        "response": response,
        "sources": sources,
    }
