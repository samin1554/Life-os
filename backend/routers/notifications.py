"""Notification router for Life OS."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from core.database import get_db
from services.notifications import (
    create_notification,
    get_notifications,
    get_unread_count,
    mark_read,
    mark_all_read,
    delete_notification,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None


class NotificationOut(BaseModel):
    id: uuid.UUID
    notification_type: str
    title: str
    message: str
    link: Optional[str]
    read: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List notifications for the current user."""
    notifications = await get_notifications(db, user.id, unread_only, limit)
    return [
        {
            "id": n.id,
            "notification_type": n.notification_type,
            "title": n.title,
            "message": n.message,
            "link": n.link,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def unread_count(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get unread notification count."""
    count = await get_unread_count(db, user.id)
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Mark a notification as read."""
    success = await mark_read(db, notification_id, user.id)
    return {"success": success}


@router.patch("/read-all")
async def mark_all_notifications_read(
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Mark all notifications as read."""
    count = await mark_all_read(db, user.id)
    return {"marked_read": count}


@router.delete("/{notification_id}")
async def dismiss_notification(
    notification_id: uuid.UUID,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a notification."""
    success = await delete_notification(db, notification_id, user.id)
    return {"success": success}
