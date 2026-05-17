"""Agent capabilities registry — single source of truth for inter-agent awareness."""

AGENT_CAPABILITIES = {
    "research": {
        "name": "Research Agent",
        "can_do": "Search the web for current information, compare options, find studies and data from trusted sources",
        "icon": "search",
    },
    "worker": {
        "name": "Worker Agent",
        "can_do": "Create downloadable documents (Word, Excel, PDF) with data, charts, and professional formatting",
        "icon": "file-text",
    },
    "health": {
        "name": "Health Agent",
        "can_do": "Analyze check-in data (mood, sleep, energy, exercise) and identify patterns over time",
        "icon": "heart",
    },
    "focus": {
        "name": "Focus Agent",
        "can_do": "Help prioritize tasks, plan the day, and suggest what to work on next",
        "icon": "target",
    },
    "goals": {
        "name": "Goals Agent",
        "can_do": "Track long-term goals, suggest milestones, and identify goal drift",
        "icon": "flag",
    },
    "execution": {
        "name": "Execution Agent",
        "can_do": "Draft text content like emails, outlines, plans, and summaries",
        "icon": "pen-tool",
    },
    "email": {
        "name": "Email Agent",
        "can_do": "Read Gmail inbox, search emails, view threads, and draft replies (never auto-sends)",
        "icon": "mail",
    },
}


def get_collaboration_prompt(exclude: str) -> str:
    """Build a system prompt section listing other agents' capabilities.

    Args:
        exclude: The current agent's name (won't be listed as a suggestion target).

    Returns:
        A prompt section instructing the LLM how and when to suggest handoffs.
    """
    agent_lines = []
    for key, cap in AGENT_CAPABILITIES.items():
        if key == exclude:
            continue
        agent_lines.append(f"- {cap['name']} ({key}): {cap['can_do']}")

    agents_list = "\n".join(agent_lines)

    return f"""
## Collaboration — Suggesting Next Steps

You can suggest follow-up actions that involve other specialist agents. When appropriate,
include a JSON block at the VERY END of your response (after all your text):

```json
{{"suggested_actions": [{{"label": "Short button text", "message": "The full message to send to trigger the next agent", "agent_hint": "agent_name", "icon": "lucide_icon_name"}}]}}
```

Available agents you can suggest:
{agents_list}

WHEN to suggest (be selective — only 1-3 suggestions max):
- You identified a clear pattern or insight that another agent could act on
- The user has enough data to make a handoff valuable (e.g., 7+ check-ins for health patterns)
- A natural next step exists (e.g., research findings → create a document)
- The user would benefit from a deeper dive via another agent

WHEN NOT to suggest:
- The user asked a simple question that you fully answered
- There isn't enough data yet (e.g., fewer than 5 check-ins)
- The user seems to want a quick answer, not a deep workflow
- You already covered everything they need

IMPORTANT:
- The "message" field should be a natural request the user would send, written in first person
- The "agent_hint" must be one of: {", ".join(k for k in AGENT_CAPABILITIES if k != exclude)}
- The "icon" should be a lucide icon name: search, file-text, target, flag, heart, pen-tool, users, bar-chart, zap
- Keep "label" under 40 characters
- Do NOT suggest actions back to yourself ({exclude})
"""
