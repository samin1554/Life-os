"""Supervisor Agent — routes user input to the correct domain agent."""
import json
from typing import Optional

from core.llm import extract_structured


SUPERVISOR_SYSTEM_PROMPT = """You are a routing agent for Life OS, a personal life coaching system.
Your ONLY job is to classify the user's input and decide which specialist agents to invoke.

Available agents: focus, health, execution, chaos_triage, goals, delegate, research, worker, email, onboarding, none

CRITICAL: Route based on what the user is ASKING YOU TO DO, not the topic they mention.
- "Write me a document about ADHD" → execution (they want you to CREATE something)
- "I've been feeling tired from poor sleep" → health (they want health ADVICE)
- "Make me a meal plan" → execution (they want you to PRODUCE something)
- "Help me plan my study schedule" → focus (they want PRIORITIZATION help)

CRITICAL DISTINCTION — research vs worker:
- The Research Agent searches the web and returns structured text findings. It does NOT create files.
- The Worker Agent creates downloadable documents (Word, Excel, PDF). It does NOT search the web.
- These are SEPARATE agents. Only combine them when the user EXPLICITLY asks for both.

Rules (in priority order):
1. If the user is just chatting, greeting, saying thanks, asking a general question, or making small talk → return "none"
2. If the user is asking a follow-up question about a previous response → return "none"
3. If the user is new and hasn't completed onboarding → invoke onboarding
4. If the user mentions being overwhelmed, too much to do, or panicking → invoke chaos_triage
5. If the user asks about their email, inbox, unread messages, or wants to check/read/search emails → invoke email
6. If the user asks to reply to an email or draft an email response → invoke email
7. If the user asks you to research, look up, compare, or find current information from the web → invoke research ONLY
8. If the user asks you to CREATE a document, spreadsheet, PDF, or formatted file → invoke worker ONLY
9. If the user asks you to PRODUCE something else (write, draft, create, make, build, generate, outline, summarize) that is NOT a file and NOT an email reply → invoke execution
10. If the user asks you to research something AND create a file → invoke research then worker (pipeline)
11. If it's a morning check-in → invoke health + focus in parallel
12. If it mentions a long-term goal or dream → invoke goals
14. If it's about sleep, energy, exercise, or physical health and asks for advice → invoke health
15. If it's about daily tasks, planning, or focus → invoke focus

PIPELINE ROUTING — ONLY return multiple agents when the user explicitly asks for multiple steps:
- "Plan a trip and create a document/guide/spreadsheet" → ["execution", "research", "worker"]
- "Research X and make a spreadsheet/report/document" → ["research", "worker"]
- "Create a budget/tracker spreadsheet for X" → ["execution", "worker"]
- "Research X" → ["research"] (NO worker — they only want web research)
- "Find prices for X" → ["research"] (NO worker — they only want data)
- "Make me a document/report about X" → ["execution", "worker"] (NO research — worker uses existing knowledge)
- "Compare A and B" → ["research"] (NO worker unless they say "and make a spreadsheet")

When returning a pipeline, list agents in execution order. Each agent's output feeds into the next.

Return ONLY a JSON object in this exact format:
{"agents": ["agent1"], "order": "sequential", "reason": "one sentence why"}

The "order" field must be either "sequential" or "parallel".
"""


async def classify_intent(user_message: str, context: Optional[str] = None, user_id=None, db=None) -> dict:
    """
    Classify user intent and return routing decision.
    Returns: {"agents": [...], "order": "sequential|parallel", "reason": "..."}
    """
    messages = [{"role": "user", "content": user_message}]
    if context:
        messages.insert(0, {"role": "user", "content": f"Context: {context}"})

    try:
        result = await extract_structured(
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            messages=messages,
            max_tokens=256,
            user_id=user_id,
            db=db,
        )

        # Validate the result
        agents = result.get("agents", ["focus"])
        if not isinstance(agents, list):
            agents = [str(agents)]

        # Ensure only valid agents
        valid_agents = {
            "focus",
            "health",
            "execution",
            "chaos_triage",
            "goals",
            "delegate",
            "research",
            "worker",
            "email",
            "onboarding",
            "synthesis",
            "none",
        }
        agents = [a for a in agents if a in valid_agents]

        if not agents:
            agents = ["none"]

        return {
            "agents": agents,
            "order": result.get("order", "sequential"),
            "reason": result.get("reason", "Defaulting to focus agent."),
        }
    except Exception:
        # Fallback if LLM fails — keyword-based routing
        msg = user_message.lower()
        if any(
            w in msg
            for w in [
                "overwhelm",
                "too much",
                "panic",
                "stressed",
                "can't handle",
                "don't know where to start",
                "piling up",
            ]
        ):
            return {
                "agents": ["chaos_triage"],
                "order": "sequential",
                "reason": "User appears overwhelmed.",
            }
        elif any(
            w in msg
            for w in [
                "research",
                "look up",
                "compare",
                "find current",
                "what's the price",
                "best",
            ]
        ):
            # Only include worker if user EXPLICITLY asks for file creation
            if any(
                w in msg
                for w in [
                    "create a document",
                    "create a spreadsheet",
                    "create a pdf",
                    "make a document",
                    "make a spreadsheet",
                    "make a pdf",
                    "make me a",
                    "generate a",
                    "and create",
                    "and make",
                    "spreadsheet",
                    "excel file",
                ]
            ):
                return {
                    "agents": ["research", "worker"],
                    "order": "sequential",
                    "reason": "User wants research compiled into a file.",
                }
            return {
                "agents": ["research"],
                "order": "sequential",
                "reason": "User asked for research only.",
            }
        elif any(
            w in msg
            for w in [
                "create a document",
                "create a spreadsheet",
                "create a pdf",
                "make a document",
                "make a spreadsheet",
                "make a pdf",
                "generate a document",
                "generate a spreadsheet",
                "generate a pdf",
                "spreadsheet",
                "excel",
                "budget tracker",
                "csv",
                "pdf",
                "word doc",
            ]
        ):
            return {
                "agents": ["worker"],
                "order": "sequential",
                "reason": "User asked for a file to be created.",
            }
        elif any(
            w in msg
            for w in [
                "inbox",
                "gmail",
                "check my mail",
                "check my email",
                "unread email",
                "reply to",
                "draft a reply",
                "read my email",
                "email from",
            ]
        ):
            return {
                "agents": ["email"],
                "order": "sequential",
                "reason": "User asked about their email/inbox.",
            }
        elif any(
            w in msg
            for w in [
                "write",
                "draft",
                "create",
                "make me",
                "generate",
                "outline",
                "summarize",
                "build me",
            ]
        ):
            return {
                "agents": ["execution"],
                "order": "sequential",
                "reason": "User asked for task execution.",
            }
        elif any(
            w in msg
            for w in [
                "sleep",
                "energy",
                "tired",
                "exercise",
                "health",
                "sick",
                "feel terrible",
                "feel awful",
            ]
        ):
            return {
                "agents": ["health"],
                "order": "sequential",
                "reason": "User mentioned health.",
            }
        elif any(
            w in msg
            for w in [
                "goal",
                "dream",
                "aim",
                "want to achieve",
                "working toward",
                "learn guitar",
                "learn to",
            ]
        ):
            return {
                "agents": ["goals"],
                "order": "sequential",
                "reason": "User mentioned goals.",
            }
        else:
            return {
                "agents": ["none"],
                "order": "sequential",
                "reason": "Casual conversation, no specialist needed.",
            }
