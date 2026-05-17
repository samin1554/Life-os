# 01 — System Architecture

## Overview

Life OS uses a **supervisor multi-agent architecture** built on LangGraph. A central supervisor agent routes every user interaction to the correct domain specialist. All agents share a common memory layer (Mem0) and a common state object, but each has its own system prompt, tools, and scratchpad.

A nightly background job (APScheduler) runs the Pattern Learning Agent independently of user sessions, processing the day's logs and updating the user's behavioural model.

---

## High-Level Data Flow

```
User Input (chat / check-in / task dump)
        │
        ▼
FastAPI Backend (Python)
        │
        ▼
LangGraph Supervisor Agent
  ├── reads: Mem0 memory (who is this user, what do they need)
  ├── reads: PostgreSQL (today's logs, goals, tasks, history)
  ├── decides: which domain agent(s) to invoke
        │
        ├──▶ Focus Agent        → priority plan, time blocking
        ├──▶ Health Agent       → sleep, energy, movement nudges
        ├──▶ Execution Agent    → drafts emails, docs, spreadsheets
        ├──▶ Chaos Triage Agent → emergency mode, 3-task collapse
        ├──▶ Relationships Agent→ social nudges, message drafts
        ├──▶ Goals Agent        → long-term tracking, drift alerts
        └──▶ Delegate Agent     → research, admin, web tasks
        │
        ▼
Synthesis Agent (runs after domain agents)
  ├── reads all domain agent outputs
  ├── spots cross-domain conflicts ("gym on your worst energy day")
  └── produces final unified response
        │
        ▼
SSE Stream → Next.js Frontend (user sees agents thinking in real time)
        │
        ▼
Response stored to PostgreSQL + Mem0 memory updated
```

---

## Nightly Pattern Learning Loop (runs at 02:00 local time)

```
APScheduler triggers Pattern Learning Job
        │
        ▼
Reads last 7 days of:
  - check-in logs (mood, energy, tasks completed vs skipped)
  - task duration actuals vs estimates
  - time-of-day completion patterns
  - which agent outputs the user approved vs overrode
        │
        ▼
Pattern Learning Agent processes data:
  - updates energy rhythm model (peak / low windows)
  - recalibrates time estimation bias (user typically underestimates by X%)
  - flags new cross-domain correlations
  - decays old patterns that no longer hold
        │
        ▼
Writes updated user profile to:
  - PostgreSQL (structured pattern data)
  - Mem0 (semantic memory update: "user's peak focus is 10am–12pm on weekdays")
```

---

## Actor-Aware Memory Model

Every memory stored in Mem0 is tagged with its source actor:

| Tag | Meaning | Trust level |
|---|---|---|
| `user_stated` | User said this directly | Highest — never overridden |
| `agent_inferred` | An agent concluded this from behaviour | Medium — can be updated |
| `pattern_learned` | Nightly learning job extracted this | Medium — decays over time |
| `system_default` | Fallback before enough data | Lowest — replaced quickly |

This prevents a critical failure mode: one agent's inference being treated as ground truth by a downstream agent.

---

## Orchestration Pattern: Supervisor (v1)

For v1, we use the **supervisor pattern** — not a full swarm.

Why: The supervisor pattern is more accurate because routing is its only job. A dedicated LLM call with a focused routing prompt misroutes far less than a peer-to-peer swarm. We graduate to LangGraph Swarm in v2 once we have usage data confirming routing is reliable and latency is the bottleneck.

```
User message
     │
     ▼
Supervisor Agent (routing only)
  - system prompt: "You are a router. Classify the intent and delegate."
  - reads: intent category, urgency, user context
  - outputs: which agent(s) to invoke, in what order
     │
     ├──▶ Agent A runs, writes to shared state
     ├──▶ Agent B runs, reads state from A, writes its output
     └──▶ Synthesis Agent reads all outputs, produces final response
```

---

## State Object (shared across all agents in a session)

```python
class LifeOSState(TypedDict):
    messages: list[BaseMessage]       # full conversation history this session
    user_id: str                       # identifies user across memory + DB
    active_agent: str                  # which agent is currently running
    domain_outputs: dict               # each agent's output this turn
    user_memories: list[dict]          # top-k retrieved memories for this turn
    user_profile: dict                 # structured profile from DB
    energy_level: str                  # current energy: high / medium / low
    chaos_mode: bool                   # if True, triage agent takes over
    task_context: list[dict]           # today's tasks and their status
    final_response: str                # assembled after synthesis
```

---

## Component Boundaries

```
┌─────────────────────────────────────────────┐
│  Next.js Frontend                           │
│  - SSE consumer (real-time agent stream)    │
│  - Dashboard, check-in UI, task queue       │
│  - No business logic — pure presentation    │
└────────────────┬────────────────────────────┘
                 │ HTTP / SSE
┌────────────────▼────────────────────────────┐
│  FastAPI Backend                            │
│  - Auth (JWT)                               │
│  - Route handlers → LangGraph entry points  │
│  - Scheduler (APScheduler)                  │
│  - No agent logic here — pure routing       │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  LangGraph Agent Graph                      │
│  - Supervisor node                          │
│  - Domain agent nodes                       │
│  - Synthesis node                           │
│  - Tool nodes (Tavily, code interpreter)    │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴──────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────────┐
│ Mem0          │   │ PostgreSQL        │
│ (semantic     │   │ (structured logs, │
│  memory,      │   │  tasks, goals,    │
│  user facts)  │   │  check-ins)       │
└───────────────┘   └───────────────────┘
```

---

## Key Architectural Decisions

**Why FastAPI over Django?**
Async-native, faster to write, pairs naturally with LangGraph's async streaming. Django is overkill for an API backend with no server-rendered templates.

**Why LangGraph over CrewAI?**
LangGraph gives lower-level control over state, checkpointing, and the exact sequence of agent calls. CrewAI is higher abstraction but less debuggable. For a personal life system where correctness matters more than speed of setup, LangGraph is the right choice.

**Why Mem0 over raw Chroma/Pinecone?**
Mem0 handles the entire memory pipeline: extraction from conversation, deduplication, actor tagging, retrieval. Building this manually on a raw vector DB would take weeks. The free tier (10K memories, 1K retrievals/month) is sufficient for development and early users.

**Why SSE over WebSockets?**
SSE (server-sent events) is unidirectional and simpler. We only need the server to stream to the client — the client sends discrete HTTP requests. WebSockets add bidirectional complexity we don't need for this pattern.

**Why not use the LangGraph Platform (paid)?**
LangGraph the library is MIT-licensed and free. The LangGraph Platform is the paid hosting service. We self-host using Docker + PostgreSQL for checkpointing. Zero cost.
