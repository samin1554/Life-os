"""CheckIn routes."""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.security import get_current_user
from models import User, CheckIn
from schemas.checkin import CheckInCreate, CheckInUpdate, CheckInResponse, CheckInListResponse

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.post("", response_model=CheckInResponse, status_code=201)
async def create_checkin(
    checkin: CheckInCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new check-in."""
    db_checkin = CheckIn(user_id=current_user.id, **checkin.model_dump())
    db.add(db_checkin)
    await db.commit()
    await db.refresh(db_checkin)
    return db_checkin


@router.get("", response_model=CheckInListResponse)
async def list_checkins(
    checkin_type: Optional[str] = Query(None, pattern=r"^(morning|midday|evening)$"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List check-ins with optional filters."""
    query = select(CheckIn).where(CheckIn.user_id == current_user.id)
    count_query = select(func.count()).select_from(CheckIn).where(CheckIn.user_id == current_user.id)

    if checkin_type:
        query = query.where(CheckIn.checkin_type == checkin_type)
        count_query = count_query.where(CheckIn.checkin_type == checkin_type)
    if from_date:
        query = query.where(CheckIn.checkin_date >= from_date)
        count_query = count_query.where(CheckIn.checkin_date >= from_date)
    if to_date:
        query = query.where(CheckIn.checkin_date <= to_date)
        count_query = count_query.where(CheckIn.checkin_date <= to_date)

    query = query.order_by(CheckIn.checkin_date.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    checkins = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return {"checkins": list(checkins), "total": total}


@router.get("/{checkin_id}", response_model=CheckInResponse)
async def get_checkin(
    checkin_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single check-in by ID."""
    result = await db.execute(
        select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    return checkin


@router.patch("/{checkin_id}", response_model=CheckInResponse)
async def update_checkin(
    checkin_id: UUID,
    checkin_update: CheckInUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a check-in."""
    result = await db.execute(
        select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")

    update_data = checkin_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(checkin, field, value)

    await db.commit()
    await db.refresh(checkin)
    return checkin


@router.delete("/{checkin_id}", status_code=204)
async def delete_checkin(
    checkin_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a check-in."""
    result = await db.execute(
        select(CheckIn).where(CheckIn.id == checkin_id, CheckIn.user_id == current_user.id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")

    await db.delete(checkin)
    await db.commit()
    return None
