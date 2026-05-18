"""Extract memorable facts from chat conversations and save to ChromaDB.

Runs as a background task after each chat response so it doesn't block the user.
"""
import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import extract_structured
from core.memory import save_memory, retrieve_memories

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You extract key facts worth remembering from a conversation between a user and their AI life coach.

Extract ONLY facts that would be useful in future conversations. Focus on:
- Personal preferences (e.g., "prefers morning workouts", "vegetarian")
- Goals and aspirations (e.g., "wants to learn guitar", "training for a marathon")
- Habits and routines (e.g., "works from home", "studies CS at university")
- Important life context (e.g., "has a dog named Max", "lives in New York")
- Health info (e.g., "sleeps 6 hours", "has back pain")
- Work/study details (e.g., "deadline on Friday", "taking 5 courses")

Do NOT extract:
- Greetings or small talk
- Temporary states ("I'm tired today")
- Things the AI said (only extract USER facts)
- Duplicate or obvious info

Return a JSON object:
{"memories": ["fact 1", "fact 2"], "categories": ["preference", "goal"]}

If there's nothing worth remembering, return: {"memories": [], "categories": []}
"""

CATEGORY_MAP = {
    "preference": "user_preference",
    "goal": "user_goal",
    "habit": "user_habit",
    "context": "life_context",
    "health": "health_info",
    "work": "work_study",
    "study": "work_study",
}


async def extract_and_save_memories(
    user_message: str,
    assistant_response: str,
    user_id: str,
    db: AsyncSession,
) -> int:
    """Extract facts from a chat exchange and save new ones to ChromaDB.

    Returns the number of new memories saved.
    """
    try:
        messages = [
            {
                "role": "user",
                "content": f"USER said: {user_message}\n\nASSISTANT responded: {assistant_response[:500]}",
            }
        ]

        result = await extract_structured(
            system_prompt=EXTRACTION_PROMPT,
            messages=messages,
            max_tokens=300,
            user_id=user_id,
            db=db,
        )

        memories = result.get("memories", [])
        categories = result.get("categories", [])

        if not memories:
            return 0

        # Check for duplicates against existing memories
        saved = 0
        for i, memory_text in enumerate(memories):
            if not memory_text or len(memory_text) < 5:
                continue

            # Search for similar existing memories
            try:
                existing = retrieve_memories(user_id, memory_text, limit=3)
                is_duplicate = any(
                    ex.get("distance", 1.0) < 0.3  # Very similar
                    for ex in existing
                )
                if is_duplicate:
                    logger.debug("Skipping duplicate memory: %s", memory_text[:50])
                    continue
            except Exception:
                pass  # If retrieval fails, save anyway

            category = CATEGORY_MAP.get(
                categories[i] if i < len(categories) else "", "general"
            )

            try:
                save_memory(
                    user_id=user_id,
                    content=memory_text,
                    metadata={
                        "source_actor": "chat_memory_extractor",
                        "category": category,
                        "confidence": 0.8,
                    },
                )
                saved += 1
                logger.info("Saved memory for user %s: %s", user_id, memory_text[:60])
            except Exception as e:
                logger.warning("Failed to save memory: %s", e)

        return saved

    except Exception as e:
        logger.warning("Memory extraction failed: %s", e)
        return 0


def schedule_memory_extraction(
    user_message: str,
    assistant_response: str,
    user_id: str,
    db: AsyncSession,
) -> None:
    """Fire-and-forget memory extraction as a background task."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(
            extract_and_save_memories(user_message, assistant_response, user_id, db)
        )
    except RuntimeError:
        logger.debug("No event loop for background memory extraction")
