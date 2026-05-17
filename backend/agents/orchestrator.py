"""Chat orchestrator — wires Supervisor + Domain Agents + Synthesis.

MVP: sequential execution. Each agent runs one after another.
Future: parallel execution for independent agents (Focus + Health).
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from agents.supervisor import classify_intent
from agents.focus import run_focus_agent
from agents.health import run_health_agent
from agents.execution import run_execution_agent
from agents.chaos_triage import run_chaos_triage_agent
from agents.goals import run_goals_agent
from agents.delegate import run_delegate_agent
from agents.research import run_research_agent
from agents.worker import run_worker_agent
from agents.email import run_email_agent
from agents.synthesis import run_synthesis_agent

AGENT_RUNNERS = {
    "focus": run_focus_agent,
    "health": run_health_agent,
    "execution": run_execution_agent,
    "chaos_triage": run_chaos_triage_agent,
    "goals": run_goals_agent,
    "delegate": run_delegate_agent,
    "research": run_research_agent,
    "worker": run_worker_agent,
    "email": run_email_agent,
}


async def process_chat(
    user_message: str,
    user_id: str,
    db: AsyncSession,
) -> dict:
    """Process a user message through the full agent pipeline.
    
    Returns:
        {
            "response": str,  # Final natural-language response
            "agents_used": list[str],
            "agent_outputs": list[dict],
            "intent": dict,
        }
    """
    # 1. Supervisor — classify intent
    intent = await classify_intent(user_message)

    # 2. Run domain agents
    agent_outputs = []
    for agent_name in intent.get("agents", ["focus"]):
        runner = AGENT_RUNNERS.get(agent_name, run_focus_agent)
        output = await runner(user_message, user_id, db)
        agent_outputs.append(output)

    # 3. Synthesis — if multiple agents or synthesis requested
    if len(agent_outputs) > 1:
        synthesis = await run_synthesis_agent(user_message, agent_outputs, user_id=user_id, db=db)
        final_response = synthesis["response"]
    else:
        final_response = agent_outputs[0]["response"] if agent_outputs else "I'm not sure how to help with that yet."

    return {
        "response": final_response,
        "agents_used": intent.get("agents", []),
        "agent_outputs": agent_outputs,
        "intent": intent,
    }


async def process_chat_streaming(
    user_message: str,
    user_id: str,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Process a user message with streaming events for SSE.
    
    Yields events:
        {"event": "intent", "data": {...}}
        {"event": "agent_start", "data": {"agent": "focus"}}
        {"event": "agent_done", "data": {"agent": "focus", "output": {...}}}
        {"event": "synthesis", "data": {"sources": [...]}}
        {"event": "final", "data": {"response": "..."}}
    """
    # 1. Intent classification
    intent = await classify_intent(user_message)
    yield {"event": "intent", "data": intent}

    # 2. Run agents sequentially, yielding start/done events
    agent_outputs = []
    for agent_name in intent.get("agents", ["focus"]):
        yield {"event": "agent_start", "data": {"agent": agent_name}}

        runner = AGENT_RUNNERS.get(agent_name, run_focus_agent)
        output = await runner(user_message, user_id, db)
        agent_outputs.append(output)

        yield {"event": "agent_done", "data": {"agent": agent_name, "output": output}}

    # 3. Synthesis
    if len(agent_outputs) > 1:
        yield {"event": "synthesis", "data": {"sources": [o["agent"] for o in agent_outputs]}}
        synthesis = await run_synthesis_agent(user_message, agent_outputs, user_id=user_id, db=db)
        final_response = synthesis["response"]
    else:
        final_response = agent_outputs[0]["response"] if agent_outputs else "I'm not sure how to help with that yet."

    yield {"event": "final", "data": {"response": final_response}}
