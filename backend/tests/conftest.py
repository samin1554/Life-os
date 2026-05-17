import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from core.database import _get_session_maker, _dispose_engine


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for the entire test session."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_session():
    """Provide a fresh async DB session per test, all on the same event loop."""
    async with _get_session_maker()() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def _cleanup_engine(request):
    """Dispose the engine once all tests finish."""
    import asyncio

    def cleanup():
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(_dispose_engine())
        except Exception:
            pass

    request.addfinalizer(cleanup)


# --- HTTP client fixtures for router tests ---

import uuid
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from main import app
from core.security import get_current_user
from core.database import get_db
from models import User


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def client(db_session):
    """Yield an httpx.AsyncClient wired to the FastAPI app.
    
    Patches get_current_user and get_db so all requests hit our test user
    and the already-open db_session.
    """
    # Create a persistent test user for the whole client lifecycle
    test_user = User(
        email=f"router_test_{uuid.uuid4().hex[:8]}@example.com",
        name="Router Test User",
        clerk_id=f"clerk_router_{uuid.uuid4().hex[:8]}",
        onboarding_done=True,
    )
    db_session.add(test_user)
    await db_session.commit()
    await db_session.refresh(test_user)

    async def _mock_get_current_user():
        return test_user

    async def _mock_get_db():
        yield db_session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[get_db] = _mock_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.user_id = test_user.id
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Dummy auth headers — Clerk is bypassed in tests."""
    return {"Authorization": "Bearer test-token"}
