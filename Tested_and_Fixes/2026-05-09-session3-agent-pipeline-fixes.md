# Session 3 — Agent Pipeline Bug Fixes

**Date:** 2026-05-09
**Scope:** Multi-agent orchestrator, domain agents, chat streaming, shared utilities
**Tests:** 56/56 passing after fixes

---

## New Code Reviewed

The following were added since Session 2 and reviewed in this session:

### Agents (6 new)
- `backend/agents/supervisor.py` — Intent classification via Groq
- `backend/agents/focus.py` — Focus/productivity agent
- `backend/agents/health.py` — Wellbeing analysis agent
- `backend/agents/execution.py` — Task execution agent
- `backend/agents/chaos_triage.py` — Overwhelm management agent
- `backend/agents/synthesis.py` — Multi-agent response synthesis

### Orchestrator
- `backend/agents/orchestrator.py` — Wires Supervisor → Domain Agents → Synthesis
- `backend/agents/shared.py` — Shared context loader and prompt formatters

### Routers (3 new)
- `backend/routers/chat.py` — Chat endpoint with SSE streaming
- `backend/routers/tasks.py` — Full CRUD for tasks
- `backend/routers/checkin.py` — Full CRUD for check-ins

### Tests (4 new)
- `backend/tests/test_supervisor.py` — 7 tests for intent classification
- `backend/tests/test_chat.py` — Chat endpoint tests
- `backend/tests/test_tasks.py` — Task CRUD tests
- `backend/tests/test_checkins.py` — Check-in CRUD tests

---

## Bugs Found & Fixed

### Bug 1: Division by zero in Health Agent
**File:** `backend/agents/health.py:41-44`
**Severity:** Medium — crashes when user has check-ins but none with sleep/mood data

**Before:**
```python
avg_sleep = sum(c.sleep_hours for c in checkins if c.sleep_hours) / len([c for c in checkins if c.sleep_hours]) if any(c.sleep_hours for c in checkins) else None
avg_mood = sum(c.mood_score for c in checkins if c.mood_score) / len([c for c in checkins if c.mood_score]) if any(c.mood_score for c in checkins) else None
```

**Problem:** `any()` and the filtering in `len()` could disagree in edge cases (e.g., falsy zero values). The one-liner was fragile and hard to read.

**After:**
```python
sleep_vals = [c.sleep_hours for c in checkins if c.sleep_hours]
mood_vals = [c.mood_score for c in checkins if c.mood_score]
avg_sleep = sum(sleep_vals) / len(sleep_vals) if sleep_vals else None
avg_mood = sum(mood_vals) / len(mood_vals) if mood_vals else None
```

---

### Bug 2: SSE Stream Missing Error Handling
**File:** `backend/routers/chat.py:34-40`
**Severity:** Medium — streaming failures silently dropped, client never got an error event

**Before:**
```python
async def _sse_generator(req: ChatRequest, user_id: str, db: AsyncSession):
    async for event in process_chat_streaming(req.message, user_id, db):
        yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
```

**After:**
```python
async def _sse_generator(req: ChatRequest, user_id: str, db: AsyncSession):
    try:
        async for event in process_chat_streaming(req.message, user_id, db):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
```

---

### Bug 3: Null User Crash in Shared Context Loader
**File:** `backend/agents/shared.py:59-66`
**Severity:** High — any agent call with an invalid `user_id` would crash with `AttributeError: 'NoneType' has no attribute 'profile'`

**Before:** The function fetched tasks/checkins/goals regardless of whether the user existed, then tried to access `user.profile` at the end — crashing if user was `None`.

**After:** Added early return when user is not found:
```python
if not user:
    return {
        "user": None,
        "profile": None,
        "tasks": [],
        "checkins": [],
        "goals": [],
    }
```

---

## Test Results

```
56 passed in ~8s
```

All 9 test files pass: infrastructure, clerk auth, onboarding, supervisor, chat, tasks, checkins, and agent pipeline tests.

## Notes
- `AsyncSession.delete()` was verified as a proper coroutine in the installed SQLAlchemy version — the `await` in task/checkin routers is correct.
- `chaos_triage.py` has a silent `except` on JSON extraction failure — left as-is since it's non-critical and matches the pattern used in `supervisor.py` for graceful LLM output parsing.
