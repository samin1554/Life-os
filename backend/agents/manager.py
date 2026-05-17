"""Manager Agent — scans pending tasks and auto-assigns them to specialist agents."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Task
from agents.supervisor import classify_intent
from agents.runner import execute_agent_run, ALL_AGENTS
from services.notifications import create_notification

logger = logging.getLogger(__name__)

DOMAIN_AGENTS = set(ALL_AGENTS)
MAX_TASKS_PER_CYCLE = 5


async def scan_and_assign(user_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.status == "pending",
            Task.assigned_agent.is_(None),
        ).limit(MAX_TASKS_PER_CYCLE)
    )
    tasks = list(result.scalars().all())

    assigned = []
    for task in tasks:
        try:
            intent = await classify_intent(
                f"Task: {task.title}. {task.description or ''}",
            )
            agent_name = intent["agents"][0]
            if agent_name not in DOMAIN_AGENTS:
                agent_name = "execution"

            task.assigned_agent = agent_name
            await db.commit()

            interaction = await execute_agent_run(
                agent_name=agent_name,
                input_text=f"Work on this task: {task.title}. {task.description or ''}",
                user_id=user_id,
                db=db,
                task_id=task.id,
                trigger_type="manager",
            )

            assigned.append({
                "task_id": str(task.id),
                "task_title": task.title,
                "agent": agent_name,
                "status": interaction.status,
            })

            await create_notification(
                db,
                user_id=task.user_id,
                notification_type="task_assigned",
                title="Task auto-assigned",
                message=f"'{task.title}' was assigned to {agent_name}",
                link="/tasks",
            )

        except Exception:
            logger.exception("Manager failed to assign task %s", task.id)

    return assigned
