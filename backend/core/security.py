"""Clerk authentication and security utilities."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer

from core.config import get_settings
from core.database import get_db
from models import User

logger = logging.getLogger(__name__)
settings = get_settings()

# Clerk JWT verification setup
clerk_config = ClerkConfig(
    jwks_url=settings.clerk_jwks_url,
    verify_iat=True,
    leeway=5.0,
)
clerk_auth_guard = ClerkHTTPBearer(config=clerk_config, auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(clerk_auth_guard),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Verify Clerk session token and return the local User.
    Auto-creates a local User record if this is the first time the Clerk user
    has hit the backend.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # credentials.decoded contains the verified JWT payload
    payload = credentials.decoded
    if not payload or not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clerk_user_id: Optional[str] = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up local user by clerk_id
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        # First time seeing this Clerk user — auto-create local record
        email = _extract_email(payload)
        name = _extract_name(payload)

        if email:
            # Check if a user with this email already exists (legacy migration path)
            result = await db.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()

            if existing:
                existing.clerk_id = clerk_user_id
                await db.commit()
                await db.refresh(existing)
                return existing

        # Create new user — use email from JWT or generate a placeholder
        user = User(
            clerk_id=clerk_user_id,
            email=email or f"{clerk_user_id}@clerk.local",
            name=name or "User",
            timezone="UTC",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


def _extract_email(payload: dict) -> Optional[str]:
    """Extract email from Clerk JWT payload."""
    # Primary email claim in Clerk tokens
    email = payload.get("email")
    if email:
        return email
    # Fallback: primary_email_address in user object
    user_data = payload.get("user_data", {})
    return user_data.get("email")


def _extract_name(payload: dict) -> Optional[str]:
    """Extract display name from Clerk JWT payload."""
    name = payload.get("name")
    if name:
        return name

    first = payload.get("first_name", "")
    last = payload.get("last_name", "")
    full = f"{first} {last}".strip()
    if full:
        return full

    # Fallback from user_data
    user_data = payload.get("user_data", {})
    name = user_data.get("name")
    if name:
        return name
    first = user_data.get("first_name", "")
    last = user_data.get("last_name", "")
    full = f"{first} {last}".strip()
    return full if full else None
