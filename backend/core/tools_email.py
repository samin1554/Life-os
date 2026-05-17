"""Email tools for the Email Agent — factory-creates tools with user context bound."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.tools import Tool
from services.email import fetch_inbox, get_email, get_thread, create_draft

logger = logging.getLogger(__name__)


def get_email_tools(user_id: str, db: AsyncSession) -> list[Tool]:
    """Create email tools with user_id and db bound via closure.

    The tool runner calls tool.func(**args) where args come from the LLM.
    By binding user_id/db into closures, the LLM only needs to provide
    the email-specific parameters (query, email_id, etc.).
    """

    async def _read_inbox(filter: str = "in:inbox is:unread") -> dict:
        """Read the user's Gmail inbox."""
        return await fetch_inbox(user_id, db, limit=15, query=filter)

    async def _search_emails(query: str) -> dict:
        """Search emails with a Gmail search query."""
        return await fetch_inbox(user_id, db, limit=10, query=query)

    async def _get_thread(thread_id: str) -> dict:
        """Get all messages in an email thread."""
        return await get_thread(user_id, db, thread_id)

    async def _draft_reply(email_id: str, body: str) -> dict:
        """Create a draft reply to a specific email. Never sends — only drafts."""
        original = await get_email(user_id, db, email_id)
        if "error" in original:
            return original

        reply_to = original.get("from", "")
        reply_subject = f"Re: {original.get('subject', '')}"

        return await create_draft(
            user_id, db,
            to=reply_to,
            subject=reply_subject,
            body=body,
            in_reply_to=email_id,
        )

    async def _search_and_draft_reply(search_query: str, body: str) -> dict:
        """Search for an email and create a draft reply to it in one step.
        First searches Gmail, picks the first matching email, then creates
        a draft reply saved to the user's Gmail Drafts folder."""
        logger.info("search_and_draft_reply: searching for '%s'", search_query)
        results = await fetch_inbox(user_id, db, limit=5, query=search_query)
        if "error" in results:
            return results

        emails = results.get("emails", [])
        if not emails:
            return {"error": f"No emails found matching '{search_query}'"}

        # Use the first match
        email = emails[0]
        email_id = email["id"]
        logger.info("search_and_draft_reply: found email %s from %s, subject: %s",
                     email_id, email.get("from"), email.get("subject"))

        # Get the full email for reply headers
        original = await get_email(user_id, db, email_id)
        if "error" in original:
            return original

        reply_to = original.get("from", "")
        reply_subject = f"Re: {original.get('subject', '')}"

        draft_result = await create_draft(
            user_id, db,
            to=reply_to,
            subject=reply_subject,
            body=body,
            in_reply_to=email_id,
        )

        if "error" not in draft_result:
            draft_result["original_email"] = {
                "from": original.get("from"),
                "subject": original.get("subject"),
            }

        return draft_result

    return [
        Tool(
            name="read_inbox",
            description="Read the user's Gmail inbox. Returns recent emails with sender, subject, date, and snippet.",
            func=_read_inbox,
            parameters={
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "Gmail search filter. Default: 'in:inbox is:unread'. Examples: 'is:unread', 'from:boss@company.com'",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="search_emails",
            description="Search the user's Gmail. Returns matching emails with sender, subject, date, snippet, and IDs.",
            func=_search_emails,
            parameters={
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g., 'from:john', 'subject:Kaggle', 'has:attachment')",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_thread",
            description="Get the full conversation thread for an email.",
            func=_get_thread,
            parameters={
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "The thread_id from a previous read_inbox or search result",
                    },
                },
                "required": ["thread_id"],
            },
        ),
        Tool(
            name="draft_reply",
            description="Create a draft reply to an email by its ID. Saves to the user's Gmail Drafts folder. Use search_and_draft_reply instead if you don't have the email_id yet.",
            func=_draft_reply,
            parameters={
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The email ID to reply to (from a previous read_inbox or search_emails result)",
                    },
                    "body": {
                        "type": "string",
                        "description": "A fully composed email body with greeting, content, and sign-off. Do NOT just copy the user's short instruction — expand it into a proper email.",
                    },
                },
                "required": ["email_id", "body"],
            },
        ),
        Tool(
            name="search_and_draft_reply",
            description="Search for an email and create a draft reply in one step. Use this when the user says 'reply to the X email'. Searches Gmail, picks the first match, and creates a draft reply saved to Gmail Drafts.",
            func=_search_and_draft_reply,
            parameters={
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "Gmail search query to find the email (e.g., 'subject:Kaggle', 'from:john')",
                    },
                    "body": {
                        "type": "string",
                        "description": "A fully composed email body with greeting, 2-3 paragraphs, and sign-off. Expand the user's brief instruction into a proper professional email.",
                    },
                },
                "required": ["search_query", "body"],
            },
        ),
    ]
