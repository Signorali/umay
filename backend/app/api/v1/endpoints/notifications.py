"""
Notification endpoints — in-app notification inbox.

GET  /notifications              → list (with unread_only filter)
GET  /notifications/count        → unread badge count
POST /notifications/{id}/read    → mark single as read
POST /notifications/read-all     → mark all as read
DELETE /notifications/{id}       → soft-delete from inbox
"""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as PydanticModel
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import NotificationType, NotificationPriority
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotificationResponse(PydanticModel):
    id: uuid.UUID
    notification_type: NotificationType
    priority: NotificationPriority
    title: str
    body: Optional[str]
    action_url: Optional[str]
    meta: Optional[dict]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(PydanticModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(PydanticModel):
    count: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    unread_only: bool = Query(False),
    notification_type: Optional[NotificationType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    """List notifications for the current user, newest first."""
    svc = NotificationService(session)
    items, total = await svc.list_for_user(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        unread_only=unread_only,
        notification_type=notification_type,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    unread = await svc.unread_count(current_user.id, current_user.tenant_id)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        unread_count=unread,
    )


@router.get("/count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Fast unread count for badge indicators. Lightweight — no pagination."""
    svc = NotificationService(session)
    count = await svc.unread_count(current_user.id, current_user.tenant_id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID = Path(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    session: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    svc = NotificationService(session)
    notif = await svc.mark_read(notification_id, current_user.id)
    await session.commit()
    if not notif:
        from fastapi import HTTPException
        raise HTTPException(404, "Notification not found")
    return NotificationResponse.model_validate(notif)


@router.post("/read-all")
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read."""
    svc = NotificationService(session)
    count = await svc.mark_all_read(current_user.id, current_user.tenant_id)
    await session.commit()
    return {"marked_read": count}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: uuid.UUID = Path(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    session: AsyncSession = Depends(get_db),
):
    """Soft-delete a notification (remove from inbox)."""
    svc = NotificationService(session)
    await svc.delete(notification_id, current_user.id)
    await session.commit()
