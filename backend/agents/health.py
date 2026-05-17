"""Health Agent — wellbeing analysis, sleep/energy/mood insights."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import chat_completion
from agents.shared import (
    get_user_context,
    format_checkins_for_prompt,
    format_profile_for_prompt,
    extract_suggested_actions,
)
from agents.registry import get_collaboration_prompt


SYSTEM_PROMPT = """You are the Health Agent for Life OS, an AI life coach.

Your job is to help the user understand and improve their physical and mental wellbeing.
You have access to their check-in history (sleep, mood, energy, stress, exercise) and profile.

Guidelines:
- Be empathetic but evidence-based. Cite their actual data.
- Highlight patterns (e.g., "Your energy drops after 6h sleep").
- Give ONE specific, actionable recommendation per response.
- Do NOT diagnose medical conditions. Suggest seeing a professional if needed.
- Celebrate wins (consistent exercise, good sleep streaks).
- Use their preferred coaching tone if specified.
"""


async def run_health_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    """Run the Health Agent.

    Returns:
        {
            "agent": "health",
            "response": str,
            "checkin_count": int,
            "suggested_actions": list[dict],
        }
    """
    ctx = await get_user_context(user_id, db)

    # Compute simple stats
    checkins = ctx["checkins"]
    sleep_vals = [c.sleep_hours for c in checkins if c.sleep_hours]
    mood_vals = [c.mood_score for c in checkins if c.mood_score]
    avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else None
    avg_mood = sum(mood_vals) / len(mood_vals) if mood_vals else None
    exercise_count = sum(1 for c in checkins if c.exercised)

    stats_block = ""
    if avg_sleep is not None:
        stats_block += f"\nAverage sleep (last {len(checkins)} checkins): {avg_sleep:.1f}h"
    if avg_mood is not None:
        stats_block += f"\nAverage mood: {avg_mood:.1f}/5"
    if checkins:
        stats_block += f"\nExercise days: {exercise_count}/{len(checkins)}"

    # Data maturity signal for collaboration suggestions
    data_maturity = "sufficient" if len(checkins) >= 7 else "early"
    if checkins and len(checkins) >= 2:
        date_range = abs((checkins[0].checkin_date - checkins[-1].checkin_date).days)
        stats_block += f"\nData span: {date_range} days ({len(checkins)} checkins, {data_maturity} for pattern analysis)"
    else:
        stats_block += f"\nData span: {len(checkins)} checkins ({data_maturity} for pattern analysis)"

    context_block = f"""USER PROFILE:
{format_profile_for_prompt(ctx['profile'])}

RECENT CHECK-INS ({len(checkins)}):
{format_checkins_for_prompt(checkins)}
{stats_block}
"""

    # Build system prompt with collaboration awareness
    full_prompt = SYSTEM_PROMPT + get_collaboration_prompt("health")

    messages = [
        {"role": "user", "content": f"{context_block}\n\nUser message: {user_message}"},
    ]

    response = await chat_completion(full_prompt, messages, max_tokens=1000, user_id=user_id, db=db)

    # Parse out suggested actions from the response
    clean_response, suggestions = extract_suggested_actions(response)

    return {
        "agent": "health",
        "response": clean_response,
        "checkin_count": len(checkins),
        "suggested_actions": suggestions,
    }
