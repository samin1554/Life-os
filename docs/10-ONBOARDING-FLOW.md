# 10 — Onboarding Flow

The onboarding agent's complete conversation design. This is the most important first impression.

---

## Design Principles

1. **One question at a time.** Never ask two things in one message.
2. **Acknowledge before moving on.** The agent responds to what the user said before asking the next question.
3. **Conversational, not clinical.** No forms, no dropdowns, no bullet lists.
4. **Extract and save immediately.** After each user response, the agent saves memory before asking the next question.
5. **10 minutes maximum.** If it takes longer, it's asking too much.

---

## The 10 Questions

Each question has: what we're asking, what memory we extract, and how to acknowledge before moving on.

### Q1: Introduction
**Ask:** "Hi! I'm really glad you're here. Before I can help you properly, I'd love to get to know you a bit. What's your name, and what brought you to Life OS today?"

**Extract:**
```python
memory.add("User's name is {name}", metadata={"category": "identity", "source_actor": "user"})
memory.add("User's initial motivation: {motivation}", metadata={"category": "context"})
```

**Acknowledge example:** "It's great to meet you, Sam. Feeling overwhelmed and avoiding the small stuff is really common — and honestly, that gap between knowing what to do and actually doing it is exactly what I'm built for."

---

### Q2: The Core Struggle
**Ask:** "What's the thing that piles up most for you? The tasks or parts of life that you keep putting off, even though you know they're not that hard?"

**Extract:**
```python
memory.add("User's primary avoidance pattern: {avoidance}", metadata={"category": "avoidance_pattern"})
```

**Acknowledge example:** "Email is a really common one — that blank compose window can feel like a wall. Knowing this helps me understand where to step in first."

---

### Q3: Life Domains
**Ask:** "If you think about your life in broad areas — like health, work, relationships, personal goals — which 2 or 3 feel most out of balance right now?"

**Extract:**
```python
profile.update(life_focus_areas=[...])
memory.add("User's priority life domains: {domains}", metadata={"category": "life_priorities"})
```

---

### Q4: A Good Day
**Ask:** "Tell me what a genuinely good day looks like for you. Not perfect — just a day where you feel like things worked."

**Extract:**
```python
memory.add("User's description of a good day: {description}", metadata={"category": "wellbeing_baseline"})
# Extract implicit signals: morning person? social energy? deep work blocks?
```

---

### Q5: A Bad Day
**Ask:** "And what typically derails a day for you? What's the first sign things are going sideways?"

**Extract:**
```python
memory.add("User's bad day pattern: {pattern}", metadata={"category": "risk_signals"})
memory.add("User's early warning signs: {signals}", metadata={"category": "mood_triggers"})
```

---

### Q6: Energy Rhythm
**Ask:** "Do you have a sense of when during the day you feel sharpest? Some people are morning people, others hit their stride after lunch. What's your honest pattern?"

**Extract:**
```python
profile.update(
    typical_wake_time=extract_time(response),
    peak_energy_start=extract_peak_start(response)
)
memory.add("User's self-reported energy peak: {time}", metadata={"category": "energy_pattern", "source_actor": "user"})
```

---

### Q7: Important People
**Ask:** "Who are the 2 or 3 people most important to you right now — people you want to make sure you stay connected with?"

**Extract:**
```python
for person in extracted_people:
    db.create_relationship(user_id, name=person.name, relationship_type=person.type)
    memory.add(f"Important person: {person.name}, {person.context}", metadata={"category": "relationships"})
```

---

### Q8: Current Goals
**Ask:** "Is there something you're working toward right now — or something you've been meaning to start? Could be big or small."

**Extract:**
```python
for goal in extracted_goals:
    db.create_goal(user_id, title=goal.title, domain=goal.domain)
    memory.add(f"User's goal: {goal.title}. Reason: {goal.why}", metadata={"category": "goals"})
```

---

### Q9: Communication Style
**Ask:** "Last thing — how do you like to be communicated with? Some people want direct, no-nonsense feedback. Others prefer a gentler approach. What works best for you?"

**Extract:**
```python
profile.update(communication_style=extract_style(response))  # "direct" | "gentle" | "detailed" | "brief"
memory.add("User's communication preference: {style}", metadata={"category": "preferences", "source_actor": "user"})
```

---

### Q10: Closing + Confirmation
**Ask:** (No question — agent summarises and confirms)

"Here's what I've got:

Your biggest friction points are {avoidance_summary}. You feel best when {good_day_summary}. The areas you want to improve most are {domains}. And you prefer {communication_style} communication.

Does that feel right? Anything you'd change or add?"

**After confirmation:**
```python
profile.update(onboarding_complete=True)
user.update(onboarding_done=True)
# Save final summary as a core memory
memory.add(
    f"Core profile summary for {user.name}: {summary}",
    metadata={"category": "core_profile", "source_actor": "user", "confidence": 1.0}
)
```

---

## Memory Extraction Prompt (used after each Q&A exchange)

This mini-prompt runs after each user message during onboarding to extract clean facts:

```python
EXTRACTION_PROMPT = """
Extract factual memories from this exchange. Return as a JSON list of memories.
Each memory should be a single, atomic fact stated or strongly implied by the user.
Do not infer — only extract what is clearly present.

Exchange:
Agent: {agent_message}
User: {user_message}

Return format:
[
  {"content": "...", "category": "...", "confidence": 0.9}
]

Categories: identity, preferences, avoidance_pattern, energy_pattern, goals,
            relationships, wellbeing_baseline, risk_signals, life_priorities
"""
```

---

## Onboarding State Machine

```
NEW_USER
    │
    ▼
GREETING (Q1)
    │
    ▼
STRUGGLE (Q2)
    │
    ▼
DOMAINS (Q3)
    │
    ▼
GOOD_DAY (Q4)
    │
    ▼
BAD_DAY (Q5)
    │
    ▼
ENERGY (Q6)
    │
    ▼
PEOPLE (Q7)
    │
    ▼
GOALS (Q8)
    │
    ▼
STYLE (Q9)
    │
    ▼
CONFIRMATION (Q10)
    │
    ├── User confirms → COMPLETE
    └── User corrects → re-process correction → COMPLETE
```

State stored in Redis (keyed by session_id) so the conversation survives page refreshes.

---

## What Onboarding Creates

After a completed onboarding, the following records exist:

**PostgreSQL:**
- 1 `user_profiles` row with structured data
- 1–3 `goals` rows
- 2–3 `relationships` rows

**Mem0:**
- 15–25 atomic memory facts tagged `user_stated`
- 1 core profile summary memory

**This is the foundation everything else builds on.**
