"""Chat routes — AI life coach with automatic agent dispatch."""
import uuid
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from core.llm import chat_completion
from models import User, ChatMessage
from schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse, ChatMessageOut
from agents.shared import (
    get_user_context,
    format_tasks_for_prompt,
    format_checkins_for_prompt,
    format_goals_for_prompt,
    format_profile_for_prompt,
)
from agents.supervisor import classify_intent
from agents.runner import execute_agent_run, AGENT_DISPLAY_NAMES, ALL_AGENTS
from core.memory_extractor import schedule_memory_extraction

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/chat", tags=["chat"])

COACH_SYSTEM_PROMPT = """You are the Life OS AI Coach — a supportive, practical personal assistant.

You help the user plan their day, reflect on progress, manage stress, and stay on track with their goals.

Key guidelines:
- Be concise and warm. Use bullet points for action items.
- Reference the user's actual tasks, goals, check-ins, and profile when relevant.
- You have specialist agents working behind the scenes. When they provide analysis, weave it naturally into your response — don't say "the Focus Agent says" or mention agents by name, just incorporate the advice as your own coaching.
- Respect their energy patterns and coaching tone preferences.

{user_context}
"""

AGENT_AUGMENTED_PROMPT = """
## Specialist Analysis
The following analysis was produced by a specialist system. Present these insights naturally in your own voice as part of your coaching response. Do not mention that a specialist or agent produced this — just incorporate the advice seamlessly.

{agent_output}
"""


def _build_context_block(ctx: dict) -> str:
    parts = []
    parts.append(f"## Profile\n{format_profile_for_prompt(ctx.get('profile'))}")
    parts.append(f"## Tasks\n{format_tasks_for_prompt(ctx.get('tasks', []))}")
    parts.append(f"## Recent Check-ins\n{format_checkins_for_prompt(ctx.get('checkins', []))}")
    parts.append(f"## Active Goals\n{format_goals_for_prompt(ctx.get('goals', []))}")
    user = ctx.get("user")
    if user:
        parts.insert(0, f"## User\nName: {user.name} | Timezone: {user.timezone}")
    return "\n\n".join(parts)


async def _load_history(
    db: AsyncSession, user_id, session_id: uuid.UUID, limit: int = 20
) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    rows = list(result.scalars().all())
    rows.reverse()
    return [{"role": r.role, "content": r.content} for r in rows]


@router.post("", response_model=ChatResponse)
@limiter.limit("15/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id = uuid.UUID(req.session_id) if req.session_id else uuid.uuid4()

    ctx = await get_user_context(str(current_user.id), db)
    context_block = _build_context_block(ctx)

    # Retrieve relevant memories for this message
    memory_block = ""
    try:
        from core.memory import retrieve_memories
        memories = retrieve_memories(str(current_user.id), req.message, limit=5)
        if memories:
            memory_items = [m["content"] for m in memories if m.get("content")]
            if memory_items:
                memory_block = "\n\n## Remembered Context\n" + "\n".join(f"- {m}" for m in memory_items)
    except Exception as e:
        logger.debug("Memory retrieval failed: %s", e)

    system_prompt = COACH_SYSTEM_PROMPT.format(user_context=context_block + memory_block)

    history = await _load_history(db, current_user.id, session_id)
    messages = history + [{"role": "user", "content": req.message}]

    agent_used = None
    agent_display_name = None
    download_url = None
    agents_pipeline = None
    suggested_actions = None
    email_draft = None

    try:
        recent_context = None
        if history:
            last_messages = history[-4:]
            recent_context = "\n".join(
                f"{m['role']}: {m['content'][:200]}" for m in last_messages
            )
        intent = await classify_intent(req.message, context=recent_context, user_id=str(current_user.id), db=db)
        agents = intent.get("agents", ["none"])

        # Filter out "none" and invalid agents
        pipeline = [a for a in agents if a != "none" and a in ALL_AGENTS]

        if pipeline:
            accumulated_context = ""
            last_interaction = None
            agents_pipeline = pipeline

            # Build recent chat context so agents know what the user was discussing
            recent_chat_context = ""
            if history:
                last_few = history[-6:]
                recent_chat_context = "\n".join(
                    f"{m['role'].upper()}: {m['content'][:300]}" for m in last_few
                )

            for agent_name in pipeline:
                input_text = req.message
                if recent_chat_context:
                    input_text = f"{req.message}\n\nRecent conversation context:\n{recent_chat_context}"
                if accumulated_context:
                    input_text += f"\n\nContext from previous analysis:\n{accumulated_context}"

                interaction = await execute_agent_run(
                    agent_name=agent_name,
                    input_text=input_text,
                    user_id=str(current_user.id),
                    db=db,
                    trigger_type="chat",
                )

                if interaction.status == "completed" and interaction.full_response:
                    accumulated_context += f"\n\n[{agent_name} output]:\n{interaction.full_response}"
                    last_interaction = interaction

            if last_interaction and last_interaction.full_response:
                system_prompt += AGENT_AUGMENTED_PROMPT.format(
                    agent_output=accumulated_context
                )
                agent_used = pipeline[-1]  # Report the last agent in pipeline
                agent_display_name = AGENT_DISPLAY_NAMES.get(agent_used, agent_used)

                # Check if worker produced a file (from metadata)
                if "worker" in pipeline and last_interaction.extra_metadata:
                    meta = last_interaction.extra_metadata
                    if isinstance(meta, dict):
                        if meta.get("download_url"):
                            download_url = meta["download_url"]
                        elif meta.get("file_id"):
                            download_url = f"/files/{meta['file_id']}/download"

                # Extract suggested actions from the last agent
                if last_interaction.extra_metadata:
                    meta = last_interaction.extra_metadata
                    if isinstance(meta, dict) and meta.get("suggested_actions"):
                        suggested_actions = meta["suggested_actions"]
                    if isinstance(meta, dict) and meta.get("email_draft"):
                        email_draft = meta["email_draft"]

    except Exception as e:
        logger.warning(f"Agent dispatch failed, falling back to direct coach: {e}")

    response_text = await chat_completion(
        system_prompt, messages, user_id=current_user.id, db=db
    )

    user_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="user",
        content=req.message,
    )
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        session_id=session_id,
        role="assistant",
        content=response_text,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    # Extract and save memories in the background (non-blocking)
    schedule_memory_extraction(
        user_message=req.message,
        assistant_response=response_text,
        user_id=str(current_user.id),
        db=db,
    )

    return ChatResponse(
        response=response_text,
        session_id=str(session_id),
        agent_used=agent_used,
        agent_display_name=agent_display_name,
        download_url=download_url,
        agents_pipeline=agents_pipeline,
        suggested_actions=suggested_actions,
        email_draft=email_draft,
    )


@router.get("/latest-session")
async def get_latest_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's most recent chat session ID (for cross-device persistence)."""
    result = await db.execute(
        select(ChatMessage.session_id)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(desc(ChatMessage.created_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"session_id": None}
    return {"session_id": str(row)}


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == current_user.id,
            ChatMessage.session_id == sid,
        )
        .order_by(ChatMessage.created_at)
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[
            ChatMessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
