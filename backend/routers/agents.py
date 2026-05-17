"""Agent routes — run, track, and monitor domain agents."""
from datetime import datetime, timezone, date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from core.redis_client import subscribe_agent_events
from models import User, AgentInteraction
from schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunListResponse,
    AgentStatusCard,
    AgentStatusResponse,
    AgentFeedbackRequest,
)
from agents.runner import execute_agent_run, AGENT_DISPLAY_NAMES, ALL_AGENTS

router = APIRouter(prefix="/agents", tags=["agents"])


def _validate_agent(name: str) -> None:
    if name not in AGENT_DISPLAY_NAMES:
        raise HTTPException(404, f"Unknown agent: {name}. Valid: {ALL_AGENTS}")


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    cards: list[AgentStatusCard] = []

    for name, display in AGENT_DISPLAY_NAMES.items():
        latest = (
            await db.execute(
                select(AgentInteraction)
                .where(
                    AgentInteraction.user_id == current_user.id,
                    AgentInteraction.agent_name == name,
                )
                .order_by(desc(AgentInteraction.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        count_result = await db.execute(
            select(func.count())
            .select_from(AgentInteraction)
            .where(
                AgentInteraction.user_id == current_user.id,
                AgentInteraction.agent_name == name,
                func.date(AgentInteraction.created_at) == today,
            )
        )
        runs_today = count_result.scalar() or 0

        if latest and latest.status == "running":
            status = "running"
        elif latest:
            status = "idle"
        else:
            status = "idle"

        cards.append(
            AgentStatusCard(
                name=name,
                display_name=display,
                status=status,
                last_run_at=latest.completed_at or latest.started_at if latest else None,
                last_output_summary=latest.output_summary if latest else None,
                runs_today=runs_today,
            )
        )

    return AgentStatusResponse(agents=cards)


@router.post("/{name}/run", response_model=AgentRunResponse, status_code=202)
async def trigger_agent_run(
    name: str,
    body: AgentRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_agent(name)

    interaction = await execute_agent_run(
        agent_name=name,
        input_text=body.input_text,
        user_id=str(current_user.id),
        db=db,
        task_id=body.task_id,
        trigger_type="manual",
    )
    return interaction


@router.get("/{name}/runs", response_model=AgentRunListResponse)
async def list_agent_runs(
    name: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_agent(name)

    base = select(AgentInteraction).where(
        AgentInteraction.user_id == current_user.id,
        AgentInteraction.agent_name == name,
    )

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        base.order_by(desc(AgentInteraction.created_at))
        .offset(offset)
        .limit(limit)
    )
    runs = result.scalars().all()

    return AgentRunListResponse(runs=runs, total=total)


@router.get("/{name}/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    name: str,
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_agent(name)

    result = await db.execute(
        select(AgentInteraction).where(
            AgentInteraction.id == run_id,
            AgentInteraction.user_id == current_user.id,
            AgentInteraction.agent_name == name,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(404, "Run not found")
    return interaction


@router.post("/{name}/runs/{run_id}/feedback", response_model=AgentRunResponse)
async def submit_feedback(
    name: str,
    run_id: UUID,
    body: AgentFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _validate_agent(name)

    result = await db.execute(
        select(AgentInteraction).where(
            AgentInteraction.id == run_id,
            AgentInteraction.user_id == current_user.id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(404, "Run not found")

    interaction.accepted = body.accepted
    if not body.accepted:
        interaction.overridden = True
        interaction.override_note = body.override_note

    await db.commit()
    await db.refresh(interaction)
    return interaction


@router.get("/events")
async def agent_events_sse(
    current_user: User = Depends(get_current_user),
):
    async def event_stream():
        async for event in subscribe_agent_events(str(current_user.id)):
            import json
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
