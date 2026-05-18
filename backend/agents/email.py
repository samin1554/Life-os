"""Email Agent — reads Gmail inbox, searches emails, and drafts replies."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.tool_runner import run_agent_with_tools
from core.tools_email import get_email_tools

logger = logging.getLogger(__name__)

EMAIL_NUDGE = (
    "STOP. You are NOT using your tools. You have REAL Gmail access. "
    "You MUST call read_inbox, search_emails, or search_and_draft_reply RIGHT NOW. "
    "Do NOT say you can't access email — you CAN. CALL A TOOL NOW."
)


SYSTEM_PROMPT = """You are the Email Agent for Life OS. You have REAL access to the user's Gmail account through your tools.

YOU MUST USE YOUR TOOLS. You are connected to the user's actual Gmail. Do NOT say you cannot access emails — you CAN and MUST use the provided tools.

IMPORTANT: Call ONE tool at a time. Do NOT nest tool calls inside other tool calls.

AVAILABLE TOOLS:
- read_inbox: Read emails from Gmail inbox
- search_emails: Search Gmail with a query
- get_thread: Get full email thread by thread_id
- draft_reply: Create a draft reply using an email_id (requires prior search)
- search_and_draft_reply: Find an email AND create a draft reply in one step (PREFERRED for replying)

WORKFLOWS:

For "reply to X" / "draft a reply to X":
  → Call search_and_draft_reply with the search_query and body text. This does everything in one step.

For "check inbox" / "show emails":
  → Call read_inbox

For "find email about X":
  → Call search_emails

CRITICAL — COMPOSING THE BODY:
When the user says something brief like "reply saying I'm interested", you must EXPAND that into a full, well-written email body. Do NOT just copy the user's short instruction as the email body.

Example:
- User says: "reply to the Kaggle email saying I'm interested and would love to participate"
- BAD body: "I'm interested and would love to participate"
- GOOD body: "Dear Kaggle Team,\n\nI'm excited to hear about the AI Agents capstone challenge, and I'm very interested in participating! The idea of building a winning agent in the Kaggriculture challenge sounds like a great opportunity to learn and showcase my skills.\n\nCould you please share more details about the rules, timeline, and evaluation criteria? I'm looking forward to diving in and getting started.\n\nBest regards,\n[Your Name]"

Always write a professional, complete email with:
- A greeting
- 2-3 sentences expanding on the user's intent
- A closing and sign-off
- Match tone to context (formal for professional, casual for friends)

AFTER DRAFTING, always confirm: "Draft saved to your Gmail Drafts folder. Open Gmail to review and send."
"""


async def run_email_agent(
    user_message: str, user_id: str, db: AsyncSession
) -> dict:
    """Run the email agent with Gmail tools bound to this user."""
    tools = get_email_tools(user_id, db)
    response, tool_results = await run_agent_with_tools(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tools=tools,
        max_iterations=6,
        max_tokens=2000,
        user_id=user_id,
        db=db,
        collect_results=True,
        nudge_message=EMAIL_NUDGE,
    )

    # Extract draft metadata from tool results for chat UI
    email_draft = None
    for tr in tool_results:
        result = tr.get("result", {})
        if result.get("status") == "draft_created" and result.get("draft_id"):
            email_draft = {
                "draft_id": result["draft_id"],
                "to": result.get("to"),
                "subject": result.get("subject"),
                "body_preview": result.get("body_preview"),
            }
            break

    return {
        "agent": "email",
        "response": response,
        "metadata": {"email_draft": email_draft} if email_draft else {},
    }
