"""Task routes."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.security import get_current_user
from models import User, Task
from schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, TaskAssignRequest
from agents.runner import execute_agent_run, ALL_AGENTS

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    db_task = Task(user_id=current_user.id, **task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, pattern=r"^(pending|in_progress|completed|cancelled)$"),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with optional filters."""
    query = select(Task).where(Task.user_id == current_user.id)
    count_query = select(func.count()).select_from(Task).where(Task.user_id == current_user.id)

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if category:
        query = query.where(Task.category == category)
        count_query = count_query.where(Task.category == category)

    query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {"tasks": list(tasks), "total": total}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single task by ID."""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return None


@router.post("/{task_id}/assign", response_model=TaskResponse)
async def assign_task_to_agent(
    task_id: UUID,
    body: TaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.agent not in ALL_AGENTS:
        raise HTTPException(400, f"Unknown agent: {body.agent}. Valid: {ALL_AGENTS}")

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.assigned_agent = body.agent
    await db.commit()

    if body.run_immediately:
        context = f"Task: {task.title}"
        if task.description:
            context += f"\nDetails: {task.description}"
        await execute_agent_run(
            agent_name=body.agent,
            input_text=context,
            user_id=str(current_user.id),
            db=db,
            task_id=task.id,
            trigger_type="manual",
        )

    await db.refresh(task)
    return task


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    context = f"Task: {task.title}"
    if task.description:
        context += f"\nDetails: {task.description}"
    if task.category:
        context += f"\nCategory: {task.category}"

    interaction = await execute_agent_run(
        agent_name="execution",
        input_text=context,
        user_id=str(current_user.id),
        db=db,
        task_id=task.id,
        trigger_type="manual",
    )

    await db.refresh(task)

    return {
        "task_id": str(task.id),
        "title": task.title,
        "execution_output": task.execution_output,
        "agent_run_id": str(interaction.id),
        "status": interaction.status,
    }
