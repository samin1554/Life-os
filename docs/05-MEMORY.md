# 05 — Memory Architecture

How Life OS learns who you are and gets smarter over time.

---

## The Core Problem Memory Solves

Without memory, every session starts from zero. The agent doesn't know your name, your goals, your struggles, or anything you said yesterday. It's a chatbot, not a coach.

With memory, the system accumulates a model of you that grows richer every day. After 2 weeks it knows your peak energy window. After 4 weeks it knows you always underestimate tasks. After 8 weeks it knows your mood drops when you haven't exercised in 3 days. This is what makes it feel like a real personal assistant.

---

## Two Memory Systems Working Together

Life OS uses two complementary memory systems:

### 1. Mem0 — Semantic Memory (the "who you are" layer)
Stores facts, preferences, patterns, and context as vector embeddings. Retrieval is semantic similarity — "find everything relevant to this user's focus and energy patterns."

**What it stores:**
- Facts stated by the user: "I hate morning calls", "I work best alone", "My sister's name is Maria"
- Inferred preferences: "User consistently completes creative tasks faster than admin tasks"
- Patterns learned: "User's peak productivity window is Tuesday–Thursday 10am–12pm"
- Relationship context: "User's manager tends to send tasks on Friday afternoons"

**Self-hosted setup:**
```python
from mem0 import Memory
import os

config = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "lifeos_memories",
            "path": "./chroma_db",  # local persistent storage
        }
    },
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-haiku-4-5-20251001",  # cheap model for extraction
            "api_key": os.environ["ANTHROPIC_API_KEY"]
        }
    },
    "embedder": {
        "provider": "anthropic",
        "config": {
            "model": "voyage-3",  # Anthropic's embedding model
        }
    }
}

memory = Memory.from_config(config)
```

### 2. PostgreSQL — Structured Memory (the "what you did" layer)
Stores timestamped logs, numerical data, and structured records that need to be queried, aggregated, and analysed. Vector search can't efficiently answer "what was the user's average mood score last week" — SQL can.

**What it stores:**
- Daily check-in logs (mood score, energy score, sleep hours)
- Task history (created, completed, skipped, duration estimate vs actual)
- Goal progress logs
- Relationship interaction logs
- Agent interaction history (what was suggested, what was accepted/overridden)

---

## The 4 Learning Layers

### Layer 1: Explicit (What you tell it)
- Source: Onboarding interview + direct corrections during use
- Trust level: Highest — never overridden by inferences
- Storage: Mem0, tagged `{"source": "user_stated", "confidence": 1.0}`
- Example: "I prefer direct feedback, not sugar-coated" → stored immediately, never contradicted

### Layer 2: Behavioural (What your actions reveal)
- Source: Task completion patterns, check-in data, which suggestions you accept/ignore
- Trust level: Medium — can be updated as behaviour changes
- Storage: PostgreSQL (raw logs) + Mem0 (extracted patterns)
- Example: User estimates tasks at 30 min, always takes 50 min → stored as `{"time_bias": 1.67, "updated": "2026-01-15"}`
- Updated: Every time a task is completed, the bias is recalculated as a rolling average

### Layer 3: Cross-domain (What the synthesis agent spots)
- Source: Pattern Learning Agent's nightly analysis
- Trust level: Medium — flagged as inferred, not stated
- Storage: Mem0, tagged `{"source": "pattern_learned", "confidence": 0.7}`
- Example: "User's mood scores are consistently 1–2 points lower on days following less than 6 hours of sleep" → stored, used by Health Agent to adjust recommendations

### Layer 4: Temporal (How you change over time)
- Source: Weekly Review Agent, long-range pattern analysis
- Trust level: Context-dependent — old patterns decay
- Storage: Mem0 with expiry metadata + PostgreSQL trend tables
- Example: "User struggled with email avoidance in weeks 1–4 but completion rate improved to 80% by week 8" → system acknowledges growth, reduces urgency of email nudges

---

## Actor-Aware Memory Tagging

Every memory stored has a `source_actor` tag. This prevents a critical failure: one agent's guess becoming another agent's assumed fact.

```python
# When saving a user-stated memory:
memory.add(
    messages=[{"role": "user", "content": "I hate morning calls"}],
    user_id=user_id,
    metadata={
        "source_actor": "user",       # stated directly by user
        "confidence": 1.0,
        "category": "preferences",
        "domain": "work"
    }
)

# When saving an agent-inferred memory:
memory.add(
    messages=[{"role": "assistant", "content": "User consistently avoids email tasks for 3+ days"}],
    user_id=user_id,
    metadata={
        "source_actor": "pattern_learning_agent",  # inferred by agent
        "confidence": 0.72,
        "category": "avoidance_pattern",
        "domain": "focus",
        "last_updated": "2026-01-15"
    }
)
```

When an agent retrieves memories, it can filter by `source_actor`:
```python
# Focus Agent only wants high-confidence user-stated preferences:
memories = memory.search(
    query="user work preferences and energy patterns",
    user_id=user_id,
    filters={"confidence": {"gte": 0.8}}
)
```

---

## Memory Retrieval Pattern (Every Agent Call)

Before any agent runs, the system retrieves the top-k relevant memories for this user and this query:

```python
async def get_agent_context(user_id: str, query: str) -> dict:
    # 1. Retrieve semantic memories from Mem0
    memories = memory.search(query=query, user_id=user_id, limit=10)

    # 2. Get structured profile from PostgreSQL
    profile = await db.get_user_profile(user_id)

    # 3. Get today's logs
    today_logs = await db.get_today_logs(user_id)

    # 4. Get current tasks
    tasks = await db.get_active_tasks(user_id)

    return {
        "memories": memories,
        "profile": profile,
        "today": today_logs,
        "tasks": tasks
    }
```

This context is injected into every agent's system prompt at runtime. The agent always knows who it's talking to.

---

## Memory Schema in Mem0

Mem0 stores memories as atomic facts with metadata. Here's what each memory entry looks like:

```json
{
  "id": "mem_abc123",
  "user_id": "user_xyz",
  "memory": "User's peak focus window is 10am to 12pm on weekdays",
  "metadata": {
    "source_actor": "pattern_learning_agent",
    "confidence": 0.84,
    "category": "energy_pattern",
    "domain": "focus",
    "created_at": "2026-01-10",
    "last_updated": "2026-01-20",
    "observation_count": 14
  }
}
```

---

## Memory Decay Strategy

Old patterns that no longer hold should not keep influencing recommendations. We handle this two ways:

**1. Time-weighted confidence:**
Pattern memories have their confidence score decayed over time if not reinforced:
- Every 7 days without reinforcement: confidence × 0.95
- If confidence drops below 0.4: memory is flagged for review
- If a new conflicting pattern emerges: old memory is updated, not duplicated

**2. Explicit override:**
If the user corrects an inference ("actually I work best in the evenings now"):
- Old memory confidence set to 0
- New user-stated memory added with confidence 1.0
- Pattern Learning Agent is notified to recalibrate

---

## Privacy: What Is Never Stored

The following are never sent to any external service:
- Raw conversation transcripts (only extracted facts go to Mem0)
- Medical information beyond what the user explicitly shares
- Financial account details or numbers
- Passwords or credentials of any kind
- Location data

The user can delete all their memories at any time:
```python
memory.delete_all(user_id=user_id)  # Mem0
await db.delete_all_user_data(user_id)  # PostgreSQL
```
