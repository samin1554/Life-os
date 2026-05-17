"""Test Clerk authentication flow."""
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from core.security import _extract_email, _extract_name, get_current_user
from models import User


def test_extract_email_direct():
    assert _extract_email({"email": "sam@example.com"}) == "sam@example.com"


def test_extract_email_from_user_data():
    assert _extract_email({"user_data": {"email": "sam@example.com"}}) == "sam@example.com"


def test_extract_email_missing():
    assert _extract_email({}) is None


def test_extract_name_direct():
    assert _extract_name({"name": "Sam Doe"}) == "Sam Doe"


def test_extract_name_from_parts():
    assert _extract_name({"first_name": "Sam", "last_name": "Doe"}) == "Sam Doe"


def test_extract_name_first_only():
    assert _extract_name({"first_name": "Sam"}) == "Sam"


def test_extract_name_missing():
    assert _extract_name({}) is None


@pytest.mark.asyncio(loop_scope="session")
async def test_auto_create_user_from_clerk(db_session):
    """Verify that get_current_user auto-creates a local User for new Clerk users."""
    test_clerk_id = f"clerk_test_{uuid.uuid4().hex[:8]}"
    test_email = f"{test_clerk_id}@example.com"

    result = await db_session.execute(select(User).where(User.clerk_id == test_clerk_id))
    existing = result.scalar_one_or_none()
    if existing:
        await db_session.delete(existing)
        await db_session.commit()

    mock_credentials = MagicMock()
    mock_credentials.decoded = {
        "sub": test_clerk_id,
        "email": test_email,
        "first_name": "Test",
        "last_name": "User",
    }

    user = await get_current_user(mock_credentials, db_session)
    assert user.clerk_id == test_clerk_id
    assert user.email == test_email
    assert user.name == "Test User"

    user2 = await get_current_user(mock_credentials, db_session)
    assert user2.id == user.id

    await db_session.delete(user)
    await db_session.commit()
