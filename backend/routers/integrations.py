"""OAuth integrations router — connect external services (Gmail, etc.)."""
import asyncio
import base64
import logging
import secrets
import traceback
from datetime import datetime, timezone
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from google_auth_oauthlib.flow import Flow

from core.config import get_settings
from core.database import get_db
from core.security import get_current_user
from core.encryption import encrypt_value, decrypt_value
from core.redis_client import get_async_redis
from models.models import User, ConnectedAccount
from services.email import send_draft as email_send_draft, _get_credentials, _get_gmail_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/integrations", tags=["integrations"])

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/userinfo.email",
]

# OAuth state and PKCE verifiers are stored in Redis with 10-min TTL
_OAUTH_STATE_TTL = 600  # 10 minutes

_CLIENT_CONFIG = {
    "web": {
        "client_id": "",  # filled at runtime
        "client_secret": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [],
    }
}


def _get_gmail_flow() -> Flow:
    """Create a Google OAuth flow for Gmail."""
    config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    return flow


@router.get("/gmail/auth-url")
async def gmail_auth_url(current_user: User = Depends(get_current_user)):
    """Generate Google OAuth URL for Gmail connection."""
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Generate a cryptographically secure state token (don't expose user_id)
    state = secrets.token_urlsafe(32)

    flow = _get_gmail_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    # Store state → {user_id, code_verifier} in Redis with TTL
    r = await get_async_redis()
    import json as _json
    state_data = _json.dumps({
        "user_id": str(current_user.id),
        "code_verifier": flow.code_verifier or "",
    })
    await r.setex(f"oauth_state:{state}", _OAUTH_STATE_TTL, state_data)

    return {"auth_url": auth_url, "state": state}


@router.get("/gmail/callback")
async def gmail_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback — exchange code for tokens and store."""
    try:
        # Verify state parameter from Redis (prevents CSRF and state forgery)
        import json as _json
        r = await get_async_redis()
        state_data = await r.get(f"oauth_state:{state}")
        if not state_data:
            logger.warning("Gmail callback: invalid or expired OAuth state")
            return RedirectResponse(url=f"{settings.frontend_url}/settings?error=gmail_failed")

        # Delete state immediately (one-time use)
        await r.delete(f"oauth_state:{state}")

        parsed_state = _json.loads(state_data)
        user_id = parsed_state["user_id"]
        code_verifier = parsed_state.get("code_verifier") or None
        logger.info("Gmail callback: user_id=%s, code_len=%d", user_id, len(code))

        # Exchange code for tokens (synchronous — run in thread)
        import os
        def _exchange_code():
            # Allow Google to return additional scopes (openid, profile)
            os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
            flow = _get_gmail_flow()
            flow.code_verifier = code_verifier
            flow.fetch_token(code=code)
            return flow.credentials

        credentials = await asyncio.to_thread(_exchange_code)
        logger.info("Gmail token exchange successful")

        # Get user email via userinfo (synchronous — run in thread)
        def _get_user_email():
            from googleapiclient.discovery import build
            service = build("oauth2", "v2", credentials=credentials)
            return service.userinfo().get().execute()

        user_info = await asyncio.to_thread(_get_user_email)
        account_email = user_info.get("email", "unknown")
        logger.info("Gmail user email: %s", account_email)

        # Delete existing Gmail connection for this user (replace)
        await db.execute(
            delete(ConnectedAccount).where(
                ConnectedAccount.user_id == user_id,
                ConnectedAccount.provider == "gmail",
            )
        )

        # Store encrypted tokens
        account = ConnectedAccount(
            user_id=user_id,
            provider="gmail",
            account_email=account_email,
            encrypted_access_token=encrypt_value(credentials.token),
            encrypted_refresh_token=encrypt_value(credentials.refresh_token or ""),
            token_expires_at=credentials.expiry.replace(tzinfo=timezone.utc) if credentials.expiry else None,
            scopes=GMAIL_SCOPES,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        logger.info("Gmail connected for user %s (%s)", user_id, account_email)

        # Redirect to frontend settings page
        return RedirectResponse(url=f"{settings.frontend_url}/settings?connected=gmail")

    except Exception as e:
        logger.error("Gmail OAuth callback failed: %s\n%s", e, traceback.format_exc())
        return RedirectResponse(url=f"{settings.frontend_url}/settings?error=gmail_failed")


@router.get("/status")
async def integrations_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return connected integrations for current user."""
    result = await db.execute(
        select(ConnectedAccount).where(ConnectedAccount.user_id == current_user.id)
    )
    accounts = result.scalars().all()

    return {
        "integrations": [
            {
                "provider": acc.provider,
                "account_email": acc.account_email,
                "is_active": acc.is_active,
                "connected_at": acc.connected_at.isoformat() if acc.connected_at else None,
            }
            for acc in accounts
        ]
    }


@router.delete("/gmail")
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Gmail integration."""
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == current_user.id,
            ConnectedAccount.provider == "gmail",
        )
    )
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Gmail not connected")

    # Try to revoke the token
    try:
        import httpx
        access_token = decrypt_value(account.encrypted_access_token)
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": access_token},
            )
    except Exception as e:
        logger.warning("Token revocation failed (non-critical): %s", e)

    await db.delete(account)
    await db.commit()

    return {"status": "disconnected"}


# ─── Draft Operations ──────────────────────────────────────────────

@router.post("/gmail/drafts/{draft_id}/send")
async def send_gmail_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send an existing Gmail draft. Requires explicit user approval."""
    result = await email_send_draft(str(current_user.id), db, draft_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/gmail/drafts/{draft_id}")
async def delete_gmail_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a Gmail draft."""
    creds = await _get_credentials(str(current_user.id), db)
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    service = _get_gmail_service(creds)

    try:
        def _delete():
            service.users().drafts().delete(userId="me", id=draft_id).execute()

        await asyncio.to_thread(_delete)
        return {"status": "deleted"}
    except Exception as e:
        logger.error("Failed to delete draft %s: %s", draft_id, e)
        raise HTTPException(status_code=400, detail=f"Failed to delete draft: {str(e)}")


@router.put("/gmail/drafts/{draft_id}")
async def update_gmail_draft(
    draft_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a Gmail draft body."""
    creds = await _get_credentials(str(current_user.id), db)
    if not creds:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    service = _get_gmail_service(creds)
    new_body = body.get("body", "")

    try:
        def _update():
            # Get existing draft to preserve headers
            draft = service.users().drafts().get(userId="me", id=draft_id, format="full").execute()
            msg = draft["message"]
            headers = msg["payload"].get("headers", [])

            to = next((h["value"] for h in headers if h["name"].lower() == "to"), "")
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
            thread_id = msg.get("threadId")

            mime_msg = MIMEText(new_body)
            mime_msg["to"] = to
            mime_msg["subject"] = subject

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
            update_body = {"message": {"raw": raw}}
            if thread_id:
                update_body["message"]["threadId"] = thread_id

            updated = service.users().drafts().update(userId="me", id=draft_id, body=update_body).execute()
            return updated

        result = await asyncio.to_thread(_update)
        return {"status": "updated", "draft_id": result.get("id")}
    except Exception as e:
        logger.error("Failed to update draft %s: %s", draft_id, e)
        raise HTTPException(status_code=400, detail=f"Failed to update draft: {str(e)}")
