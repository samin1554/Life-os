import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from .config import get_settings

settings = get_settings()

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        # Use NullPool in tests to avoid asyncpg event loop conflicts
        # when engine.dispose() is called between tests
        poolclass = NullPool if os.environ.get("PYTEST_CURRENT_TEST") else None
        _engine = create_async_engine(
            settings.async_database_url,
            echo=settings.debug,
            future=True,
            poolclass=poolclass,
        )
    return _engine


async def _dispose_engine():
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


def _get_session_maker():
    return async_sessionmaker(
        _get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


Base = declarative_base()


async def get_db():
    async with _get_session_maker()() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> bool:
    try:
        async with _get_session_maker()() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
