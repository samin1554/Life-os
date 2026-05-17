# Life OS — Week 6 + Agent Architecture Refactor (2026-05-10)

## Overview

This session completed a major architectural refactor: **agents were transformed from hidden pipeline workers into visible, independent entities** that the user can directly interact with. The chat was simplified to a direct LLM coach conversation, while domain agents gained their own dedicated dashboard with real-time SSE status, manual task assignment, and run history. A Manager Agent now auto-assigns pending tasks every 30 minutes via APScheduler.

---

## Architecture Changes

### Before: Orchestrator Pipeline
- Chat message → `Orchestrator` → `Supervisor` → Domain Agent(s) → `Synthesis` → Response
- Agents were invisible to the user
- No tracking of what agents ran or what they produced
- Chat was tightly coupled to agent orchestration

### After: Smart Chat + Visible Agent Fleet
- **Chat**: AI Coach conversation with automatic agent dispatch. `classify_intent()` detects when a specialist agent is needed, runs it behind the scenes via `execute_agent_run()`, and weaves the output into the coach's natural response. Non-tech users just chat; agents work transparently.
- **Agents**: 9 specialist agents (Focus, Health, Execution, Chaos Triage, Goals, Relationships, Delegate, Research, Worker) with their own dashboard page.
- **Manager Agent**: Background job that scans pending tasks every 30 minutes, classifies intent, assigns to the best agent, and triggers execution.
- **Tracking**: Every agent run creates an `AgentInteraction` row with status, input/output summaries, error messages, and user feedback.
- **Events**: Redis pub/sub broadcasts agent status changes via SSE to connected frontend clients.

---

## Backend Changes

### New Files

| File | Purpose |
|------|---------|
| `agents/runner.py` | Wraps domain agents with `AgentInteraction` persistence + Redis events. `execute_agent_run()` is the single entry point for all agent execution. |
| `agents/manager.py` | `scan_and_assign()` — queries pending unassigned tasks, classifies intent via `supervisor.classify_intent()`, assigns agent, triggers run. Max 5 tasks per cycle. |
| `core/redis_client.py` | Async Redis client (`aioredis`) for agent event pub/sub. `publish_agent_event()` + `subscribe_agent_events()` for SSE. |
| `routers/agents.py` | 6 endpoints: `GET /agents/status`, `POST /agents/{name}/run`, `GET /agents/{name}/runs`, `GET /agents/{name}/runs/{id}`, `POST /agents/{name}/runs/{id}/feedback`, `GET /agents/events` (SSE) |
| `schemas/agent.py` | Pydantic v2 schemas: `AgentRunRequest`, `AgentRunResponse`, `AgentRunListResponse`, `AgentStatusCard`, `AgentStatusResponse`, `AgentFeedbackRequest` |
| `schemas/chat.py` | Schemas for chat: `ChatRequest`, `ChatResponse`, `ChatHistoryResponse`, `ChatMessageOut` |

### Modified Files

| File | Changes |
|------|---------|
| `models/models.py` | Added `assigned_agent` (str) and `execution_output` (Text) to `Task`. Extended `AgentInteraction` with `status`, `task_id`, `trigger_type`, `started_at`, `completed_at`, `error_message`. Added `ChatMessage` table (id, user_id, session_id, role, content, created_at). |
| `routers/chat.py` | Completely rewritten. Direct LLM call via `chat_completion()`. Loads last 20 `ChatMessage` rows for context. Persists user + assistant messages. System prompt instructs coach to suggest agents rather than route to them. |
| `routers/tasks.py` | Added `POST /tasks/{task_id}/assign` — sets `assigned_agent` and optionally triggers immediate run via `execute_agent_run()`. Added `POST /tasks/{task_id}/execute` — triggers Execution Agent on a task. |
| `routers/dashboard.py` | Added `agents[]` array to response — same card structure as `/agents/status` for the dashboard agent fleet strip. |
| `core/scheduler.py` | Added `_manager_scan_job()` running every 30 minutes (`CronTrigger(minute="*/30")`). Scans all onboarded users, calls `scan_and_assign()` per user with isolated error handling. |
| `main.py` | Added `agents` router import and `app.include_router(agents.router)`. |

### Database Migration

- **Migration file**: `alembic/versions/9512167cc148_add_agent_tracking_chat_messages.py`
- **Changes applied**:
  - Added `assigned_agent` (VARCHAR, nullable) and `execution_output` (TEXT, nullable) to `tasks` table
  - Added `status` (VARCHAR), `task_id` (UUID FK), `trigger_type` (VARCHAR), `started_at` (TIMESTAMP), `completed_at` (TIMESTAMP), `error_message` (TEXT) to `agent_interactions` table
  - Created `chat_messages` table with id (UUID PK), user_id (UUID FK), session_id (UUID, indexed), role (VARCHAR), content (TEXT), created_at (TIMESTAMP)

---

## Frontend Changes

### New Files

| File | Purpose |
|------|---------|
| `app/(app)/agents/page.tsx` | Agent Fleet control page. 7 interactive agent cards in a grid. Each card shows: icon, name, description, live status badge, runs-today count, last run time, last output preview, task input field, run button, expandable run history. Live Activity panel shows real-time SSE events. |
| `hooks/useAgentEvents.ts` | SSE hook connecting to `/agents/events` via `fetch` + `ReadableStream` (no `EventSource` due to auth header needs). Parses `data:` lines, maintains event log (last 50), handles reconnect with `AbortController`. Returns `{ events, connected, connect, disconnect }`. |
| `hooks/useChat.ts` | Chat hook for direct LLM conversation. `sendMessage()`, `loadHistory()`, `clearChat()`. Manages message array, session ID, loading state, errors. No SSE — standard POST/response. |
| `types/index.ts` | Central type definitions: `Task`, `CheckIn`, `Goal`, `Relationship`, `Memory`, `AgentStatusCard`, `AgentRun`, `AgentEvent`, `DashboardData`, `ChatMessage` |

### Modified Files

| File | Changes |
|------|---------|
| `app/globals.css` | Cyberpunk design system: void black (#0a0a0f), neon green (#00ff88), magenta (#ff00ff), cyan (#00d4ff), destructive (#ff3366). Scanline overlay, chamfered corners via clip-path, neon glow utilities, text glows, glitch/blink/rgb-shift/pulse-glow/fade-in-up animations, grid pattern, custom dark scrollbar, `prefers-reduced-motion` support. |
| `app/(app)/dashboard/page.tsx` | Added Agent Fleet strip — compact tiles showing agent status from `dashboard.agents[]`. |
| `app/(app)/tasks/page.tsx` | Added agent assignment dropdown on hover for each task. |
| `app/(app)/chat/page.tsx` | Rewired to use `useChat` hook. Terminal-style chat UI with message history. |
| Sidebar / layout components | Added `/agents` nav link. |

### Frontend Pages (13 total)

| Route | Group | Description |
|-------|-------|-------------|
| `/` | Public | Landing page |
| `/onboarding` | Public | Multi-step onboarding wizard |
| `/sign-in/[[...sign-in]]` | Public | Clerk sign-in |
| `/sign-up/[[...sign-up]]` | Public | Clerk sign-up |
| `/dashboard` | `(app)` | Main dashboard with tasks, goals, streaks, agent fleet |
| `/chat` | `(app)` | Direct LLM coach conversation |
| `/tasks` | `(app)` | Task CRUD + agent assignment dropdown |
| `/checkin` | `(app)` | Morning/midday/evening check-ins |
| `/goals` | `(app)` | Goal tracking with drift alerts |
| `/relationships` | `(app)` | Relationship health & nudges |
| `/agents` | `(app)` | **NEW** — Agent Fleet control center |
| `/settings` | `(app)` | User settings |

---

## Key Code Patterns

### Agent Execution Flow

```
User clicks "Run" on /agents page
  → POST /agents/{name}/run (routers/agents.py)
    → execute_agent_run() (agents/runner.py)
      1. Create AgentInteraction row (status="running")
      2. Publish Redis event: {agent, status: "running"}
      3. Call domain agent from AGENT_RUNNERS
      4. On success: update interaction (status="completed", output_summary)
         → Update Task.execution_output if task_id linked
         → Publish Redis event: {status: "completed", output_summary}
      5. On failure: update interaction (status="failed", error_message)
         → Publish Redis event: {status: "failed", error}
```

### SSE Event Flow

```
Frontend mounts /agents page
  → useAgentEvents.connect() opens fetch() to /agents/events
    → routers/agents.py agent_events_sse()
      → subscribe_agent_events(user_id) (core/redis_client.py)
        → aioredis pubsub.subscribe(f"agent_events:{user_id}")
          → async generator yields events
    → StreamingResponse sends "data: {json}\n\n" per event
  → Frontend parses data lines, updates events array
  → Agent cards re-render with live status
```

### Manager Auto-Assignment Flow

```
APScheduler triggers every 30 minutes
  → _manager_scan_job() (core/scheduler.py)
    → For each onboarded user:
      → scan_and_assign(user_id, db) (agents/manager.py)
        → Query: pending tasks WHERE assigned_agent IS NULL (LIMIT 5)
        → For each task:
          → classify_intent(task title + description)
          → Set task.assigned_agent = best_agent
          → execute_agent_run(best_agent, task_context, trigger_type="manager")
```

---

## Build & Test Status

### Backend
- **91/91 tests passing** when run together: `cd backend && python3 -m pytest tests/ -v`
- **Critical rule**: All async tests must use `@pytest.mark.asyncio(loop_scope="session")`
- **Warnings**: 2 deprecation warnings (SQLAlchemy `utcfromtimestamp`, starlette `multipart` import) — non-blocking
- No new tests added for agent router in this session — existing tests cover underlying agents

### Frontend
- **Build passes**: 13 routes, 0 errors, 0 warnings
- **Middleware deprecation**: Next.js 16 warns `"middleware" file convention is deprecated. Please use "proxy" instead.` — non-blocking
- Command: `cd frontend && npm run build`

### Infrastructure
- PostgreSQL: 5433, Redis: 6381, Chroma: 8010 (Docker Compose)
- Frontend: 3002, Backend: 8001

---

## File Inventory

### Backend (new + modified)

```
backend/
├── agents/
│   ├── runner.py              ← NEW — agent execution wrapper
│   ├── manager.py             ← NEW — auto-assign pending tasks
│   ├── orchestrator.py        ← unchanged, still maps agent_name → function
│   ├── supervisor.py          ← unchanged, classify_intent() still used
│   └── ... domain agents      ← unchanged
├── core/
│   ├── redis_client.py        ← NEW async pub/sub + modified sync onboarding
│   ├── scheduler.py           ← MODIFIED + manager_scan_job
│   ├── database.py            ← unchanged
│   ├── llm.py                 ← unchanged
│   └── security.py            ← unchanged
├── models/
│   └── models.py              ← MODIFIED + Task.assigned_agent, +ChatMessage, extended AgentInteraction
├── routers/
│   ├── agents.py              ← NEW — 6 agent endpoints
│   ├── chat.py                ← REWRITTEN — direct LLM coach
│   ├── tasks.py               ← MODIFIED + assign + execute endpoints
│   ├── dashboard.py           ← MODIFIED + agents[] in response
│   └── ... other routers      ← unchanged
├── schemas/
│   ├── agent.py               ← NEW
│   └── chat.py                ← NEW
├── main.py                    ← MODIFIED + agents router
└── alembic/versions/
    └── 9512167cc148_add_agent_tracking_chat_messages.py  ← NEW migration
```

### Frontend (new + modified)

```
frontend/
├── app/
│   ├── (app)/
│   │   ├── agents/
│   │   │   └── page.tsx       ← NEW — Agent Fleet control center
│   │   ├── dashboard/
│   │   │   └── page.tsx       ← MODIFIED + agent fleet strip
│   │   ├── chat/
│   │   │   └── page.tsx       ← MODIFIED — uses useChat hook
│   │   ├── tasks/
│   │   │   └── page.tsx       ← MODIFIED + agent assignment dropdown
│   │   └── ... other pages    ← unchanged
│   ├── globals.css            ← MODIFIED — complete cyberpunk design system
│   └── layout.tsx             ← unchanged
├── hooks/
│   ├── useAgentEvents.ts      ← NEW — SSE hook
│   └── useChat.ts             ← NEW — chat state hook
├── types/
│   └── index.ts               ← NEW — central type definitions
└── components/                ← cyber card, button, badge, input components
```

---

## Known Issues & Deferred Work

| Issue | Status | Notes |
|-------|--------|-------|
| SSE token-level streaming | **Deferred** | Currently agent-event level only. Per-token LLM streaming deferred post-MVP. |
| Middleware deprecation | **Non-blocking** | Next.js 16 warns about `middleware` convention. Upgrade to `proxy` when stable. |
| Tavily web search | **Needs API key** | `tavily-python` installed, `tavily_api_key` in config. Research Agent uses it with DuckDuckGo fallback. Add key to `.env` to activate. |
| Mobile sidebar | **Missing** | Sidebar always visible on desktop. No hamburger collapse for `< lg` screens. |
| Notification system | **Not built** | No real-time alerts for drift, nudges, check-in reminders yet. |
| Pattern insights widget | **Not displayed** | Pattern learning runs nightly but insights not shown on dashboard. |
| Weekly review viewer | **No page** | Reviews generated Sundays but no dedicated page to read them. |
| Agent router tests | **Missing** | No dedicated tests for `/agents/*` endpoints. Covered indirectly via integration. |
| Research/Worker agent tests | **Missing** | New agents (Research, Worker) have no dedicated tests yet. |
| Generated files cleanup | **Not built** | Files in `generated_files/` accumulate with no TTL or user-scoped isolation. |

---

## Environment & Configuration

```
Backend:    FastAPI 0.115, Python 3.12.6, SQLAlchemy 2.0+ (asyncpg), Alembic
Frontend:   Next.js 16.2.6, TypeScript, Tailwind v4, @clerk/nextjs v7, shadcn/ui (base-nova)
LLM:        Groq via OpenAI-compatible client — llama-3.3-70b-versatile (chat), llama-3.1-8b-instant (extraction)
Auth:       Clerk JWT verification, auto-creates local User on first visit
Tests:      pytest 8.4.2 + pytest-asyncio 0.24.0, asyncio_mode=auto, loop_scope="session"
Infra:      Docker Compose (PostgreSQL 5433, Redis 6381, Chroma 8010)
Ports:      Frontend 3002, Backend 8001, Postgres 5433, Redis 6381, Chroma 8010
```

---

## How to Verify

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -v

# Frontend build
cd frontend && npm run build

# Start infrastructure
cd backend && docker compose up -d

# Start backend
cd backend && uvicorn main:app --reload --port 8001

# Start frontend
cd frontend && npm run dev -- --port 3002
```

---

## Design Decisions

1. **Chat simplification**: Removed orchestrator/supervisor/synthesis from chat hot path because it added latency and obscured agent behavior. Users now chat directly with a coach who can *suggest* agents, keeping the agent system transparent.

2. **Visible agents**: Each agent has its own card, run history, and manual trigger. This makes the system debuggable and gives users agency over when specialist analysis runs.

3. **Redis pub/sub for SSE**: Chosen over WebSockets because events are one-way (server → client) and Redis already in stack. Per-user channel isolation via `agent_events:{user_id}`.

4. **Manager Agent as scheduler job**: Rather than a persistent background process, it's a simple async function triggered by APScheduler. This keeps state in the database (Task.assigned_agent) rather than in memory.

5. **AgentInteraction as audit log**: Every run is persisted with full input/output/error tracking. This enables debugging, feedback loops, and future pattern learning on agent performance.

---

## Session 3 — Smart Chat Auto-Dispatch + Persistent Chat

### Overview

Two features added in this session:
1. **Smart Auto-Dispatch**: The chat now automatically detects when a specialist agent is needed, runs it behind the scenes, and weaves the output into the coach's response — so non-tech users never need to visit the Agents page.
2. **Persistent Chat**: Chat history survives page navigation and browser refreshes. Messages are restored from the database on mount via `localStorage`-persisted session IDs.

---

### Smart Chat Auto-Dispatch

#### Problem
The chat was a simple direct LLM coach that told users "try the Focus Agent on the dashboard." Non-tech-savvy users would never navigate to `/agents` — they expect to just chat and get specialist help automatically.

#### Solution
The chat endpoint now runs an intent classification step before the coach LLM call:

```
User message arrives
  → classify_intent(message, recent_conversation_context)
  → If agents == ["none"]: direct coach response (casual chat)
  → If agents != ["none"]:
      1. execute_agent_run(agent, message, trigger_type="chat")
      2. Inject agent output into coach's system prompt
      3. Coach responds naturally, incorporating specialist insights
      4. Response includes agent_used metadata for frontend badge
```

#### Backend Changes

| File | Changes |
|------|---------|
| `agents/supervisor.py` | Added `"none"` classification for casual messages. Rewrote prompt with priority-ordered rules and concrete examples. Action verbs (write, create, make, draft) now take priority over topic — "make a document about ADHD" routes to Execution, not Health. Added "make me", "generate", "outline", "build me" to keyword fallback. |
| `schemas/chat.py` | Added `agent_used` (Optional[str]) and `agent_display_name` (Optional[str]) to `ChatResponse`. |
| `routers/chat.py` | Core change: imports `classify_intent` + `execute_agent_run`. After loading history, classifies intent with last 4 messages as context. If agent needed, runs it via `execute_agent_run(trigger_type="chat")`, injects output into system prompt via `AGENT_AUGMENTED_PROMPT`. Coach is instructed to present insights in its own voice. Falls back to direct coach on any error. Updated `COACH_SYSTEM_PROMPT` to remove "suggest agents on dashboard" language. |
| `tests/test_supervisor.py` | Strengthened overwhelm test message for LLM reliability. Updated fallback test to accept "none" as valid default. |

#### Frontend Changes

| File | Changes |
|------|---------|
| `types/index.ts` | Added `agent_used` and `agent_display_name` to `ChatMessage` interface. |
| `hooks/useChat.ts` | Passes `agent_used` and `agent_display_name` from API response to message objects. |
| `app/(app)/chat/page.tsx` | Shows color-coded "⚡ Powered by [Agent Name]" badge on agent-assisted messages using `AGENT_COLORS` map. Updated subtitle to "Auto-dispatches specialist agents when needed". Updated empty state copy. |

#### Key Design Decisions

1. **Action over topic routing**: The supervisor now prioritizes WHAT the user asks to DO over the topic mentioned. "Write a document about health" → Execution. "I feel sick" → Health.
2. **Conversation context for intent**: `classify_intent()` receives the last 4 messages so follow-up requests ("yes please make that document") are understood in context, not classified in isolation.
3. **Graceful fallback**: If intent classification or agent dispatch fails, the coach responds directly — the user never sees an error.
4. **trigger_type="chat"**: Agent runs from chat are tracked separately in `AgentInteraction`, visible in the agent's run history on the Agents page.

---

### Persistent Chat

#### Problem
Chat messages lived only in React state. Navigating to another page or refreshing the browser wiped the conversation.

#### Solution
The session ID is persisted in `localStorage`. On mount, the hook checks for a saved session and loads history from the backend's `GET /chat/history` endpoint.

#### Changes

| File | Changes |
|------|---------|
| `hooks/useChat.ts` | Saves `session_id` to `localStorage` after each API response. On mount, checks `localStorage` for saved session and calls `loadHistory()` to restore messages from database. `clearChat()` removes the `localStorage` key, starting a fresh session. Moved `loadHistory` above `useEffect` to fix reference ordering. |

---

### Build & Test Status

- **Backend**: 91/91 tests passing — `cd backend && python3 -m pytest tests/ -v`
- **Frontend**: Build passes — 13 routes, 0 errors, 0 warnings — `cd frontend && npm run build`

---

### File Inventory (Session 3)

```
Backend (modified):
├── agents/supervisor.py          ← "none" classification + action-over-topic priority
├── routers/chat.py               ← intent detection + agent dispatch + conversation context
├── schemas/chat.py               ← agent_used, agent_display_name on ChatResponse
└── tests/test_supervisor.py      ← stronger test messages

Frontend (modified):
├── types/index.ts                ← agent fields on ChatMessage
├── hooks/useChat.ts              ← agent metadata passthrough + localStorage persistence
└── app/(app)/chat/page.tsx       ← agent attribution badge + updated copy
```
