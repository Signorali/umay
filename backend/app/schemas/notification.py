"""Notification schemas — request/response contracts for in-app notifications."""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.notification import NotificationPriority, NotificationType


# ── Response ──────────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    notification_type: str
    priority: str
    title: str
    body: Optional[str] = None
    action_url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    items: List[NotificationOut]
    total: int
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int


# ── Request ───────────────────────────────────────────────────────────────────

class NotificationBroadcastIn(BaseModel):
    """Admin-only: broadcast a custom notification to a list of users."""
    user_ids: List[uuid.UUID] = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=300)
    body: Optional[str] = Field(None, max_length=2000)
    priority: NotificationPriority = NotificationPriority.MEDIUM
    action_url: Optional[str] = Field(None, max_length=500)
    meta: Optional[Dict[str, Any]] = None


class MarkReadIn(BaseModel):
    """Mark a list of notification IDs as read."""
    notification_ids: List[uuid.UUID] = Field(..., min_length=1)
