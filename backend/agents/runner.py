"""Agent runner — wraps domain agents with tracking and real-time events."""
import uuid
import traceback
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import AgentInteraction, Task
from core.redis_client import publish_agent_event
from agents.orchestrator import AGENT_RUNNERS
from services.notifications import create_notification

AGENT_DISPLAY_NAMES = {
    "focus": "Focus Agent",
    "health": "Health Agent",
    "execution": "Execution Agent",
    "chaos_triage": "Chaos Triage Agent",
    "goals": "Goals Agent",
    "delegate": "Delegate Agent",
    "research": "Research Agent",
    "worker": "Worker Agent",
    "email": "Email Agent",
}

ALL_AGENTS = list(AGENT_DISPLAY_NAMES.keys())


async def execute_agent_run(
    agent_name: str,
    input_text: str,
    user_id: str,
    db: AsyncSession,
    task_id: Optional[uuid.UUID] = None,
    trigger_type: str = "manual",
) -> AgentInteraction:
    runner = AGENT_RUNNERS.get(agent_name)
    if runner is None:
        raise ValueError(f"Unknown agent: {agent_name}")

    interaction = AgentInteraction(
        user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
        agent_name=agent_name,
        input_summary=input_text[:500],
        status="running",
        task_id=task_id,
        trigger_type=trigger_type,
        started_at=datetime.now(timezone.utc),
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    await publish_agent_event(user_id if isinstance(user_id, str) else str(user_id), {
        "agent": agent_name,
        "interaction_id": str(interaction.id),
        "status": "running",
        "task_id": str(task_id) if task_id else None,
    })

    try:
        output = await runner(input_text, str(user_id), db)

        interaction.status = "completed"
        interaction.completed_at = datetime.now(timezone.utc)
        interaction.output_summary = output.get("response", "")[:500]
        interaction.full_response = output.get("response", "")
        interaction.accepted = None

        # Merge metadata + suggested_actions into extra_metadata
        meta = output.get("metadata") or output.get("extra_metadata") or {}
        if output.get("suggested_actions"):
            meta["suggested_actions"] = output["suggested_actions"]
        interaction.extra_metadata = meta if meta else None

        if task_id:
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(execution_output=output.get("response", ""))
            )

        await db.commit()
        await db.refresh(interaction)

        await publish_agent_event(str(user_id), {
            "agent": agent_name,
            "interaction_id": str(interaction.id),
            "status": "completed",
            "task_id": str(task_id) if task_id else None,
            "output_summary": interaction.output_summary,
        })

        await create_notification(
            db,
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            notification_type="agent_completed",
            title=f"{AGENT_DISPLAY_NAMES.get(agent_name, agent_name)} finished",
            message=interaction.output_summary or "Agent completed successfully",
            link=f"/agents" if not task_id else f"/tasks",
        )

    except Exception as e:
        interaction.status = "failed"
        interaction.completed_at = datetime.now(timezone.utc)
        interaction.error_message = f"{type(e).__name__}: {e}"

        await db.commit()
        await db.refresh(interaction)

        await publish_agent_event(str(user_id), {
            "agent": agent_name,
            "interaction_id": str(interaction.id),
            "status": "failed",
            "error": str(e),
        })

        await create_notification(
            db,
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            notification_type="agent_failed",
            title=f"{AGENT_DISPLAY_NAMES.get(agent_name, agent_name)} failed",
            message=interaction.error_message or "An error occurred",
            link="/agents",
        )

    return interaction
