"""Gmail service layer — read inbox, get threads, create drafts."""
import asyncio
import base64
import logging
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

from core.config import get_settings
from core.encryption import encrypt_value, decrypt_value
from models.models import ConnectedAccount

logger = logging.getLogger(__name__)
settings = get_settings()


async def _get_credentials(user_id: str, db: AsyncSession) -> Optional[Credentials]:
    """Get valid Gmail credentials for user, refreshing if needed."""
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == "gmail",
            ConnectedAccount.is_active == True,
        )
    )
    account = result.scalars().first()
    if not account:
        return None

    access_token = decrypt_value(account.encrypted_access_token)
    refresh_token = decrypt_value(account.encrypted_refresh_token)

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )

    # Check if expired and refresh
    if account.token_expires_at and account.token_expires_at < datetime.now(timezone.utc):
        try:
            await asyncio.to_thread(creds.refresh, GoogleRequest())
            # Update stored tokens
            account.encrypted_access_token = encrypt_value(creds.token)
            if creds.refresh_token:
                account.encrypted_refresh_token = encrypt_value(creds.refresh_token)
            account.token_expires_at = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
            await db.commit()
            logger.info("Refreshed Gmail token for user %s", user_id)
        except Exception as e:
            logger.error("Failed to refresh Gmail token: %s", e)
            account.is_active = False
            await db.commit()
            return None

    return creds


def _get_gmail_service(credentials: Credentials):
    """Build Gmail API service client."""
    return build("gmail", "v1", credentials=credentials)


def _decode_body(payload: dict) -> str:
    """Extract text body from Gmail message payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    # Check parts recursively
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        # Nested multipart
        if part.get("parts"):
            result = _decode_body(part)
            if result:
                return result

    return ""


def _get_header(headers: list, name: str) -> str:
    """Get a header value from Gmail message headers."""
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


async def fetch_inbox(
    user_id: str, db: AsyncSession, limit: int = 15, query: str = None
) -> dict:
    """Fetch recent emails from user's Gmail inbox."""
    creds = await _get_credentials(user_id, db)
    if not creds:
        return {"error": "Gmail not connected. Ask the user to connect Gmail in Settings."}

    service = _get_gmail_service(creds)

    try:
        def _fetch():
            results = service.users().messages().list(
                userId="me",
                maxResults=limit,
                q=query or "in:inbox",
            ).execute()

            messages = results.get("messages", [])
            emails = []

            for msg_ref in messages[:limit]:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()

                headers = msg.get("payload", {}).get("headers", [])
                labels = msg.get("labelIds", [])

                emails.append({
                    "id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "from": _get_header(headers, "From"),
                    "subject": _get_header(headers, "Subject"),
                    "date": _get_header(headers, "Date"),
                    "snippet": msg.get("snippet", ""),
                    "is_unread": "UNREAD" in labels,
                })

            return {"emails": emails, "count": len(emails)}

        return await asyncio.to_thread(_fetch)

    except Exception as e:
        logger.error("Failed to fetch inbox: %s", e)
        return {"error": f"Failed to fetch inbox: {str(e)}"}


async def get_email(user_id: str, db: AsyncSession, email_id: str) -> dict:
    """Get full email content by ID."""
    creds = await _get_credentials(user_id, db)
    if not creds:
        return {"error": "Gmail not connected."}

    service = _get_gmail_service(creds)

    try:
        def _fetch():
            msg = service.users().messages().get(
                userId="me", id=email_id, format="full"
            ).execute()

            headers = msg.get("payload", {}).get("headers", [])
            body = _decode_body(msg.get("payload", {}))

            return {
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": _get_header(headers, "From"),
                "to": _get_header(headers, "To"),
                "subject": _get_header(headers, "Subject"),
                "date": _get_header(headers, "Date"),
                "body": body[:3000],
                "snippet": msg.get("snippet", ""),
            }

        return await asyncio.to_thread(_fetch)

    except Exception as e:
        logger.error("Failed to get email %s: %s", email_id, e)
        return {"error": f"Failed to get email: {str(e)}"}


async def get_thread(user_id: str, db: AsyncSession, thread_id: str) -> dict:
    """Get all messages in a thread."""
    creds = await _get_credentials(user_id, db)
    if not creds:
        return {"error": "Gmail not connected."}

    service = _get_gmail_service(creds)

    try:
        def _fetch():
            thread_data = service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()

            messages = []
            for msg in thread_data.get("messages", []):
                headers = msg.get("payload", {}).get("headers", [])
                body = _decode_body(msg.get("payload", {}))
                messages.append({
                    "id": msg["id"],
                    "from": _get_header(headers, "From"),
                    "to": _get_header(headers, "To"),
                    "subject": _get_header(headers, "Subject"),
                    "date": _get_header(headers, "Date"),
                    "body": body[:2000],
                })

            return {"thread_id": thread_id, "messages": messages, "count": len(messages)}

        return await asyncio.to_thread(_fetch)

    except Exception as e:
        logger.error("Failed to get thread %s: %s", thread_id, e)
        return {"error": f"Failed to get thread: {str(e)}"}


async def create_draft(
    user_id: str,
    db: AsyncSession,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str = None,
) -> dict:
    """Create a draft email in Gmail."""
    creds = await _get_credentials(user_id, db)
    if not creds:
        return {"error": "Gmail not connected."}

    service = _get_gmail_service(creds)

    try:
        def _create():
            mime_msg = MIMEText(body)
            mime_msg["to"] = to
            mime_msg["subject"] = subject

            # If replying, set headers for threading
            if in_reply_to:
                original = service.users().messages().get(
                    userId="me", id=in_reply_to, format="metadata",
                    metadataHeaders=["Message-ID"],
                ).execute()
                original_headers = original.get("payload", {}).get("headers", [])
                orig_message_id = _get_header(original_headers, "Message-ID")
                if orig_message_id:
                    mime_msg["In-Reply-To"] = orig_message_id
                    mime_msg["References"] = orig_message_id

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

            draft_body = {"message": {"raw": raw}}
            if in_reply_to:
                original_msg = service.users().messages().get(
                    userId="me", id=in_reply_to, format="minimal"
                ).execute()
                draft_body["message"]["threadId"] = original_msg.get("threadId")

            draft = service.users().drafts().create(userId="me", body=draft_body).execute()
            logger.info("Draft created successfully: draft_id=%s, to=%s, subject=%s", draft["id"], to, subject)

            return {
                "draft_id": draft["id"],
                "to": to,
                "subject": subject,
                "body_preview": body[:200],
                "status": "draft_created",
            }

        return await asyncio.to_thread(_create)

    except Exception as e:
        logger.error("Failed to create draft: %s", e)
        return {"error": f"Failed to create draft: {str(e)}"}


async def send_draft(user_id: str, db: AsyncSession, draft_id: str) -> dict:
    """Send an existing draft. Only called with explicit user approval."""
    creds = await _get_credentials(user_id, db)
    if not creds:
        return {"error": "Gmail not connected."}

    service = _get_gmail_service(creds)

    try:
        def _send():
            sent = service.users().drafts().send(
                userId="me", body={"id": draft_id}
            ).execute()
            return {"status": "sent", "message_id": sent.get("id")}

        return await asyncio.to_thread(_send)

    except Exception as e:
        logger.error("Failed to send draft %s: %s", draft_id, e)
        return {"error": f"Failed to send draft: {str(e)}"}
