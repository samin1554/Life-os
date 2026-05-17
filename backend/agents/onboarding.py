"""Onboarding Agent — conducts the 10-question conversational interview."""
import json
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.llm import chat_completion, extract_structured
from core.memory import save_memory
from core.redis_client import get_onboarding_state, set_onboarding_state
from models import User, UserProfile, Goal


# The 10 onboarding questions
ONBOARDING_QUESTIONS = [
    {
        "id": "intro",
        "prompt": "Hi! I'm really glad you're here. Before I can help you properly, I'd love to get to know you a bit. What's your name, and what brought you to Life OS today?",
    },
    {
        "id": "struggle",
        "prompt": "What's the thing that piles up most for you? The tasks or parts of life that you keep putting off, even though you know they're not that hard?",
    },
    {
        "id": "domains",
        "prompt": "If you think about your life in broad areas — like health, work, relationships, personal goals — which 2 or 3 feel most out of balance right now?",
    },
    {
        "id": "good_day",
        "prompt": "Tell me what a genuinely good day looks like for you. Not perfect — just a day where you feel like things worked.",
    },
    {
        "id": "bad_day",
        "prompt": "And what typically derails a day for you? What's the first sign things are going sideways?",
    },
    {
        "id": "energy",
        "prompt": "Do you have a sense of when during the day you feel sharpest? Some people are morning people, others hit their stride after lunch. What's your honest pattern?",
    },
    {
        "id": "people",
        "prompt": "Who are the 2 or 3 people most important to you right now — people you want to make sure you stay connected with?",
    },
    {
        "id": "goals",
        "prompt": "Is there something you're working toward right now — or something you've been meaning to start? Could be big or small.",
    },
    {
        "id": "style",
        "prompt": "Last thing — how do you like to be communicated with? Some people want direct, no-nonsense feedback. Others prefer a gentler approach. What works best for you?",
    },
    {
        "id": "confirm",
        "prompt": "Here's what I've got so far. Does this feel right? Anything you'd change or add?",
    },
]


EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction assistant for a personal coaching app.
Extract factual memories from the user's message. Return ONLY a JSON array of memories.
Each memory is a single, atomic fact stated or strongly implied by the user.
Do not infer — only extract what is clearly present.

Return format:
[
  {"content": "...", "category": "...", "confidence": 0.9}
]

Categories: identity, preferences, avoidance_pattern, energy_pattern, goals,
            relationships, wellbeing_baseline, risk_signals, life_priorities, coaching_style
"""


CONFIRMATION_SYSTEM_PROMPT = """You are an onboarding coach for Life OS. Summarise what you've learned about the user
in a warm, conversational way. Then ask if it feels right.

Keep it brief — 3-4 sentences max. No bullet points.
"""


async def process_onboarding_message(
    user_id: str,
    message: str,
    db: AsyncSession,
) -> dict:
    """
    Process one message in the onboarding conversation.
    Returns: {"message": str, "step": int, "total_steps": int, "complete": bool}
    """
    state = get_onboarding_state(user_id)
    step = state["step"]

    # If this is the first message and we're at step 0, just ask Q1
    if step == 0 and not state["answers"]:
        state["session_id"] = str(uuid.uuid4())
        state["step"] = 1
        set_onboarding_state(user_id, state)
        return {
            "message": ONBOARDING_QUESTIONS[0]["prompt"],
            "step": 1,
            "total_steps": 10,
            "complete": False,
        }

    # If user is responding to a question, process it
    if step >= 1 and step <= 9:
        # Store the answer
        state["answers"].append({
            "question_id": ONBOARDING_QUESTIONS[step - 1]["id"],
            "question": ONBOARDING_QUESTIONS[step - 1]["prompt"],
            "answer": message,
        })

        # Extract memories from the answer
        await _extract_and_save_memories(user_id, message, step - 1, db=db)

        # Move to next step
        state["step"] = step + 1
        set_onboarding_state(user_id, state)

        # Return the next question (or confirmation for step 10)
        if step + 1 <= 10:
            next_question = ONBOARDING_QUESTIONS[step]["prompt"]
            # For Q10 (confirmation), generate a personalised summary
            if step + 1 == 10:
                summary = await _generate_confirmation_summary(state["answers"], user_id=user_id, db=db)
                next_question = f"{summary}\n\nDoes that feel right? Anything you'd change or add?"

            return {
                "message": next_question,
                "step": step + 1,
                "total_steps": 10,
                "complete": False,
            }

    # Step 10: user confirms or corrects
    if step == 10:
        state["answers"].append({
            "question_id": "confirm",
            "question": "Confirmation",
            "answer": message,
        })
        state["complete"] = True
        set_onboarding_state(user_id, state, ttl=86400)  # Keep for 24h

        # Build profile from all answers
        await _build_user_profile(user_id, state["answers"], db)

        # Save core profile summary memory
        summary = _build_text_summary(state["answers"])
        save_memory(
            user_id,
            f"Core profile summary: {summary}",
            metadata={
                "source_actor": "onboarding_agent",
                "confidence": 1.0,
                "category": "core_profile",
                "domain": "general",
            },
        )

        return {
            "message": "Perfect. Your Life OS is ready — let's get to work.",
            "step": 10,
            "total_steps": 10,
            "complete": True,
        }

    # Fallback — should not reach here
    return {
        "message": "Something went wrong. Let's start over.",
        "step": 0,
        "total_steps": 10,
        "complete": False,
    }


async def _extract_and_save_memories(user_id: str, message: str, question_index: int, db=None) -> None:
    """Extract memories from a user answer and save them to Chroma."""
    try:
        result = await extract_structured(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": message},
            ],
            max_tokens=512,
            user_id=user_id,
            db=db,
        )

        memories = result if isinstance(result, list) else result.get("memories", [])
        if not memories and isinstance(result, dict) and "raw" not in result:
            # Fallback: wrap result as single memory if it's a dict
            if "content" in result:
                memories = [result]

        for mem in memories:
            if isinstance(mem, dict) and "content" in mem:
                save_memory(
                    user_id,
                    mem["content"],
                    metadata={
                        "source_actor": "user",
                        "confidence": mem.get("confidence", 0.9),
                        "category": mem.get("category", "general"),
                        "domain": mem.get("domain", "general"),
                    },
                )
    except Exception:
        # If extraction fails, silently continue — don't break onboarding flow
        pass


async def _generate_confirmation_summary(answers: list[dict], user_id=None, db=None) -> str:
    """Generate a personalised summary for the confirmation step."""
    try:
        # Build a concise context from answers
        context = "\n".join([
            f"Q: {a['question_id']}\nA: {a['answer'][:200]}"
            for a in answers[:8]  # Exclude style question for brevity
        ])

        summary = await chat_completion(
            system_prompt=CONFIRMATION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Here's what the user shared:\n\n{context}\n\nSummarise what I've learned about them."},
            ],
            max_tokens=256,
            user_id=user_id,
            db=db,
        )
        return summary.strip()
    except Exception:
        return "Here's what I've gathered about you so far."


async def _build_user_profile(user_id: str, answers: list[dict], db: AsyncSession) -> None:
    """Build the user's profile from onboarding answers and save to PostgreSQL."""
    # Get or create user profile
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    # Map answers to profile fields
    answer_map = {a["question_id"]: a["answer"] for a in answers}

    # life_focus_areas from domains answer
    if "domains" in answer_map:
        profile.life_focus_areas = _extract_list(answer_map["domains"])

    # communication_style from style answer
    if "style" in answer_map:
        style = answer_map["style"].lower()
        if "direct" in style:
            profile.communication_style = "direct"
        elif "gentle" in style:
            profile.communication_style = "gentle"
        elif "brief" in style:
            profile.communication_style = "brief"
        elif "detailed" in style:
            profile.communication_style = "detailed"

    # Mark user as onboarded
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.onboarding_done = True

    await db.commit()

    # Create goals from goals answer
    if "goals" in answer_map:
        goal_text = answer_map["goals"]
        # Simple heuristic: create one goal from the text
        goal = Goal(
            user_id=user_id,
            title=goal_text[:100],
            description=goal_text,
            domain="personal",
            timeframe="this_year",
        )
        db.add(goal)
        await db.commit()



def _build_text_summary(answers: list[dict]) -> str:
    """Build a plain text summary from all answers."""
    parts = []
    for a in answers:
        if a["question_id"] != "confirm":
            parts.append(f"{a['question_id']}: {a['answer'][:150]}")
    return " | ".join(parts)


def _extract_list(text: str) -> list[str]:
    """Extract a list of items from free text."""
    # Simple split by commas or newlines
    items = [i.strip() for i in text.replace("\n", ",").split(",")]
    return [i for i in items if i and len(i) > 2][:5]


def _extract_names(text: str) -> list[str]:
    """Very basic name extraction from text."""
    # Split by common separators and filter for capitalised words
    import re
    # Look for capitalised words that might be names
    candidates = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b', text)
    # Filter out common non-name words
    skip = {"The", "A", "An", "I", "You", "We", "They", "He", "She", "It", "My", "Life", "Os"}
    return [c for c in candidates if c not in skip][:5]
