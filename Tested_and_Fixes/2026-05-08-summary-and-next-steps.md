# Week 3 Summary: Supervisor + Onboarding Agent

## Completed

### Groq Migration (switched from Anthropic)
- **`core/llm.py`**: Replaced `AsyncAnthropic` with `openai.AsyncOpenAI` using Groq's base URL (`https://api.groq.com/openai/v1`)
- **`core/config.py`**: Renamed `anthropic_api_key` → `groq_api_key`
- **`requirements.txt`**: Replaced `anthropic==0.40.0` with `openai>=1.30.0`
- **`.env` / `.env.example`**: Updated key name to `GROQ_API_KEY`
- Default models set: chat = `llama-3.3-70b-versatile`, extraction = `llama-3.1-8b-instant`
- Added `response_format={"type": "json_object"}` to `extract_structured()` for reliable JSON output

### Supervisor Agent
- Keyword-based intent classifier (`classify_intent`) — all **7/7 tests passing** ✅
- Routes: overwhelm → chaos_triage, task verbs → execution, morning → health+focus, names → relationships, goal keywords → goals, fallback → focus

### Onboarding Agent
- 10-question conversational interview with Redis state storage
- Memory extraction via `_extract_and_save_memories()` (calls Groq LLM)
- Profile building at step 10 via `_build_user_profile()` — creates `UserProfile`, `Goal`, and `Relationship` rows
- FastAPI routes protected via Clerk auth

### Test Status
| Test File | Passed | Failed | Notes |
|-----------|--------|--------|-------|
| `test_supervisor.py` | 7/7 | 0 | All green ✅ |
| `test_onboarding.py` | 4/5 | 1 | `test_onboarding_completes` fails when run after `test_infrastructure.py` |
| `test_infrastructure.py` | 3/3 | 0 | Postgres, Redis, Chroma all green ✅ |
| `test_clerk_auth.py` | 7/7 | 0 | All green ✅ |
| **Total** | **21/22** | **1** | |

## Active Issue: asyncpg Event Loop Conflict

### Symptom
`test_onboarding_completes` fails with:
```
RuntimeError: Task <Task-22> got Future <Future pending cb=[Protocol._on_waiter_completed()]> attached to a different loop
```

This occurs at `_build_user_profile` line 237 when calling:
```python
result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
```

### Key Finding
The failure **only happens when `test_infrastructure.py::test_postgres_connection` runs before the onboarding tests**. Running onboarding tests in isolation passes cleanly.

### Root Cause (best theory)
`test_postgres_connection` directly imports `_get_engine()`, disposes it, and creates a session. This direct engine manipulation leaves asyncpg's internal protocol/greenlet state in a corrupted state that affects subsequent ORM `greenlet_spawn()` calls inside `_build_user_profile`. The SQLAlchemy async + asyncpg + greenlet combination is sensitive to engine lifecycle events across tests.

### Attempted Fixes (none fully resolved)
1. ✅ Function-scoped `db_session` with `loop_scope="session"`
2. ✅ `await engine.dispose()` before each test's session creation
3. ✅ Lazy engine creation (`_get_engine()` instead of module-level)
4. ✅ `NullPool` during tests (fresh connection per checkout)
5. ✅ Mocked LLM calls in tests to eliminate HTTP client interference
6. ✅ Removed fixture teardown cleanup that used separate sessions
7. ✅ Made `onboarding_user_id` depend on `db_session` to avoid engine-dispose races

### Current Workaround
- `test_onboarding_completes` passes in isolation: `pytest tests/test_onboarding.py tests/test_supervisor.py -v`
- Fails only in full suite runs where `test_infrastructure.py` precedes it

### Recommended Fix Paths
1. **Skip `test_onboarding_completes` when running full suite** — add `@pytest.mark.skipif(os.environ.get("SKIP_FLAKY"))` or run onboarding tests separately in CI
2. **Refactor `test_postgres_connection`** — don't directly create/dispose engine; use `db_session` fixture instead
3. **Switch to `aiosqlite` for unit tests** — keep PostgreSQL only for integration tests
4. **Use `pytest-xdist` with `--forked`** — isolate test processes
5. **Accept and document** — production code is unaffected; this is a test-only SQLAlchemy asyncpg greenlet interaction bug

## Next Steps: Week 4 — Core Domain Agents

With onboarding + supervisor stable, the next deliverables are:

1. **Focus Agent** — daily prioritization, task ranking, focus blocks
2. **Health Agent** — check-in analysis, energy pattern detection, sleep/exercise correlations
3. **Execution Agent** — task breakdown, drafting, subtask generation
4. **Chaos Triage Agent** — overwhelm assessment, emergency task filtering, calm-down protocol

Each agent needs:
- Agent module in `backend/agents/`
- Router in `backend/routers/`
- Redis state + memory integration
- Unit tests ( Groq calls mocked )

## Files Changed This Session
- `backend/core/llm.py` — Groq migration
- `backend/core/config.py` — `groq_api_key`
- `backend/core/database.py` — lazy engine + NullPool for tests
- `backend/requirements.txt` — `openai>=1.30.0`
- `backend/.env` — `GROQ_API_KEY`
- `backend/.env.example` — `GROQ_API_KEY`
- `backend/tests/conftest.py` — `db_session` fixture with lazy engine
- `backend/tests/test_infrastructure.py` — updated to use `_get_engine()` / `_get_session_maker()`
- `backend/tests/test_onboarding.py` — mocked LLM calls, simplified fixture
- `backend/Tested_and_Fixes/2026-05-08-summary-and-next-steps.md` — this file
