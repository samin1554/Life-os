"""Authentication routes — Clerk integration."""
import base64
import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_db
from core.security import get_current_user
from models import User
from schemas.auth import UserResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])

# Clerk webhooks use Svix format — tolerance window of 5 minutes
WEBHOOK_TOLERANCE_SECONDS = 300


def _verify_webhook_signature(payload: bytes, headers: dict[str, str], secret: str) -> None:
    """
    Verify Clerk/Svix webhook signature.
    Clerk signs webhooks using the Svix standard:
      - svix-id: message ID
      - svix-timestamp: unix timestamp
      - svix-signature: comma-separated base64 signatures (v1,<base64>)
    """
    msg_id = headers.get("svix-id") or headers.get("webhook-id", "")
    timestamp = headers.get("svix-timestamp") or headers.get("webhook-timestamp", "")
    signature_header = headers.get("svix-signature") or headers.get("webhook-signature", "")

    if not msg_id or not timestamp or not signature_header:
        raise ValueError("Missing required webhook headers (svix-id, svix-timestamp, svix-signature)")

    # Check timestamp is within tolerance
    try:
        ts = int(timestamp)
    except ValueError:
        raise ValueError("Invalid webhook timestamp")

    now = int(time.time())
    if abs(now - ts) > WEBHOOK_TOLERANCE_SECONDS:
        raise ValueError("Webhook timestamp outside tolerance window")

    # Compute expected signature
    # Secret format from Clerk: "whsec_<base64>" — strip prefix and decode
    if secret.startswith("whsec_"):
        secret_bytes = base64.b64decode(secret[6:])
    else:
        secret_bytes = base64.b64decode(secret)

    to_sign = f"{msg_id}.{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = base64.b64encode(
        hmac.new(secret_bytes, to_sign, hashlib.sha256).digest()
    ).decode("utf-8")


    # Signature header can have multiple signatures: "v1,<sig1> v1,<sig2>"
    signatures = signature_header.split(" ")
    for sig in signatures:
        parts = sig.split(",", 1)
        if len(parts) == 2 and parts[0] == "v1":
            if hmac.compare_digest(expected, parts[1]):
                return

    raise ValueError("No matching webhook signature found")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get current user profile. Requires valid Clerk session token."""
    return current_user


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receive Clerk webhooks for user lifecycle events.
    Verifies the webhook signature and handles user.created,
    user.updated, and user.deleted events.
    """
    payload = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # --- Signature verification ---
    if settings.clerk_webhook_secret:
        try:
            _verify_webhook_signature(payload, headers, settings.clerk_webhook_secret)
        except ValueError as e:
            logger.warning("Clerk webhook verification failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )
    else:
        logger.error("CLERK_WEBHOOK_SECRET not set — rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook verification not configured",
        )

    event = json.loads(payload)
    event_type = event.get("type", "")
    data = event.get("data", {})

    # --- Handle events ---
    if event_type == "user.created":
        clerk_id = data.get("id")
        email = (data.get("email_addresses") or [{}])[0].get("email_address", "")
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or email

        # Check if user already exists (from lazy creation)
        existing = await db.execute(select(User).where(User.clerk_id == clerk_id))
        if existing.scalar_one_or_none() is None:
            new_user = User(
                clerk_id=clerk_id,
                email=email,
                name=full_name,
            )
            db.add(new_user)
            await db.commit()
            logger.info("User created via webhook: clerk_id=%s, email=%s", clerk_id, email)

    elif event_type == "user.updated":
        clerk_id = data.get("id")
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            email = (data.get("email_addresses") or [{}])[0].get("email_address", "")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            if email:
                user.email = email
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                user.name = full_name
            await db.commit()
            logger.info("User updated via webhook: clerk_id=%s", clerk_id)

    elif event_type == "user.deleted":
        clerk_id = data.get("id")
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            await db.delete(user)
            await db.commit()
            logger.info("User deleted via webhook: clerk_id=%s", clerk_id)

    return {"received": True, "event": event_type}
