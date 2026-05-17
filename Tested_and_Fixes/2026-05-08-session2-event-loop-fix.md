# Life OS — Session 2 Fix Report
**Date:** 2026-05-08 (Session 2)  
**Scope:** Fix cross-test event loop contamination bug  
**Result:** 23/23 tests passing (was 22/23 + 1 error)

---

## The Bug

`test_onboarding_completes` failed with `RuntimeError: Task got Future attached to a different loop` — but ONLY when `test_infrastructure.py::test_postgres_connection` ran before it.

The onboarding test passed in isolation (`pytest tests/test_onboarding.py`), confirming cross-test contamination.

---

## Root Cause

**Event loop scope mismatch between tests and fixtures.**

The `db_session` fixture used `loop_scope="session"` (all fixtures share one event loop for the entire test session). But `test_postgres_connection` was a standalone `@pytest.mark.asyncio` test — with `asyncio_mode = auto`, this defaults to `loop_scope="function"` (its own private event loop).

The sequence that broke things:

1. `test_auto_create_user_from_clerk` runs → `db_session` fixture creates engine + session on **loop A** (session-scoped)
2. `test_postgres_connection` runs on **loop B** (function-scoped) → calls `_get_engine()` which returns the same global engine → creates connections on loop B → loop B is destroyed after test
3. `db_session` fixture runs again for onboarding tests → calls `_dispose_engine()` then `_get_session_maker()` → creates new engine on **loop A** → session works for fixture setup (INSERT user, COMMIT)
4. `test_onboarding_completes` step 10 → `_build_user_profile` calls `db.execute()` → asyncpg tries to create a connection but the engine's internal state was contaminated by the loop B interaction → **RuntimeError: Future attached to a different loop**

The previous workaround (`_dispose_engine()` in the fixture) made things worse — disposing and recreating the engine between every test amplified the loop mismatch.

---

## The Fix

Two changes:

### 1. Removed `_dispose_engine()` from `db_session` fixture
The engine is now created once (lazily) and reused for all tests. No engine disposal between tests. With `NullPool` (already configured for test mode), each DB operation gets a fresh connection anyway — no stale connection risk.

### 2. Unified all async tests onto `loop_scope="session"`
Every async test now explicitly uses `@pytest.mark.asyncio(loop_scope="session")` or `pytestmark = pytest.mark.asyncio(loop_scope="session")` (for files with only async tests). This ensures all async tests and fixtures share the same event loop — no more loop A vs loop B conflicts.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/tests/conftest.py` | Removed `_dispose_engine()` from `db_session` fixture; added session-scoped engine cleanup finalizer |
| `backend/tests/test_infrastructure.py` | `test_postgres_connection` now uses `db_session` fixture + `loop_scope="session"` instead of manual engine management |
| `backend/tests/test_clerk_auth.py` | Added `@pytest.mark.asyncio(loop_scope="session")` to async test |
| `backend/tests/test_onboarding.py` | Added `@pytest.mark.asyncio(loop_scope="session")` to all 3 async tests |
| `backend/tests/test_supervisor.py` | Added `pytestmark = pytest.mark.asyncio(loop_scope="session")` (all tests are async) |

---

## Test Results

```
$ cd backend && python -m pytest tests/ -v

tests/test_clerk_auth.py::test_extract_email_direct PASSED               [  4%]
tests/test_clerk_auth.py::test_extract_email_from_user_data PASSED       [  8%]
tests/test_clerk_auth.py::test_extract_email_missing PASSED              [ 13%]
tests/test_clerk_auth.py::test_extract_name_direct PASSED                [ 17%]
tests/test_clerk_auth.py::test_extract_name_from_parts PASSED            [ 21%]
tests/test_clerk_auth.py::test_extract_name_first_only PASSED            [ 26%]
tests/test_clerk_auth.py::test_extract_name_missing PASSED               [ 30%]
tests/test_clerk_auth.py::test_auto_create_user_from_clerk PASSED        [ 34%]
tests/test_infrastructure.py::test_postgres_connection PASSED            [ 39%]
tests/test_infrastructure.py::test_redis_connection PASSED               [ 43%]
tests/test_infrastructure.py::test_chroma_connection PASSED              [ 47%]
tests/test_onboarding.py::test_onboarding_start_returns_first_question PASSED [ 52%]
tests/test_onboarding.py::test_onboarding_advances_through_steps PASSED  [ 56%]
tests/test_onboarding.py::test_onboarding_completes PASSED               [ 60%]
tests/test_onboarding.py::test_extract_list PASSED                       [ 65%]
tests/test_onboarding.py::test_extract_names PASSED                      [ 69%]
tests/test_supervisor.py::test_classify_overwhelm PASSED                 [ 73%]
tests/test_supervisor.py::test_classify_execution PASSED                 [ 78%]
tests/test_supervisor.py::test_classify_health PASSED                    [ 82%]
tests/test_supervisor.py::test_classify_goals PASSED                     [ 86%]
tests/test_supervisor.py::test_classify_relationships PASSED             [ 91%]
tests/test_supervisor.py::test_classify_fallback PASSED                  [ 95%]
tests/test_supervisor.py::test_classify_returns_valid_structure PASSED   [100%]

======================== 23 passed, 1 warning in 9.29s =========================
```

---

## Rule for Future Tests

When adding new async tests, always use one of:

```python
# Option A: per-test (when file has mix of sync + async tests)
@pytest.mark.asyncio(loop_scope="session")
async def test_something(db_session):
    ...

# Option B: module-level (when all tests in file are async)
pytestmark = pytest.mark.asyncio(loop_scope="session")
```

This ensures all async tests share the session-scoped event loop and avoids asyncpg connection contamination.
