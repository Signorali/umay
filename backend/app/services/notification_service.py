"""
Notification Service — create, list and manage in-app notifications.

Rules:
  - Notifications are append-only; never hard-deleted (only soft-delete via is_deleted)
  - System-generated notifications use idempotency_key to prevent duplicates
  - User can mark read (single or bulk); admins can broadcast to all tenant users
  - Pagination: newest first, unread count always available
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_

from app.models.notification import Notification, NotificationType, NotificationPriority


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Notification]:
        """
        Create a notification. If idempotency_key already exists, returns None (skip duplicate).
        """
        if idempotency_key:
            existing = await self._get_by_idempotency_key(idempotency_key)
            if existing:
                return None  # already sent, skip

        notif = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            body=body,
            action_url=action_url,
            meta=meta,
            idempotency_key=idempotency_key,
        )
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def broadcast(
        self,
        tenant_id: uuid.UUID,
        user_ids: List[uuid.UUID],
        notification_type: NotificationType,
        title: str,
        body: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        idempotency_key_prefix: Optional[str] = None,
    ) -> int:
        """Send the same notification to multiple users. Returns count created."""
        created = 0
        for uid in user_ids:
            ikey = f"{idempotency_key_prefix}:{uid}" if idempotency_key_prefix else None
            result = await self.create(
                tenant_id=tenant_id,
                user_id=uid,
                notification_type=notification_type,
                title=title,
                body=body,
                priority=priority,
                action_url=action_url,
                meta=meta,
                idempotency_key=ikey,
            )
            if result:
                created += 1
        return created

    # ── Read ──────────────────────────────────────────────────────────────────

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int]:
        """List notifications for a user, newest first."""
        q = select(Notification).where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_deleted == False,
        )
        if unread_only:
            q = q.where(Notification.is_read == False)
        if notification_type:
            q = q.where(Notification.notification_type == notification_type)

        total_q = select(func.count()).select_from(q.subquery())
        total = (await self.session.execute(total_q)).scalar_one()

        items = (await self.session.execute(
            q.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        )).scalars().all()

        return list(items), total

    async def unread_count(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Fast unread count — used for badge indicator in UI."""
        result = await self.session.execute(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
        )
        return result.scalar_one()

    # ── Update ────────────────────────────────────────────────────────────────

    async def mark_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[Notification]:
        """Mark a single notification as read."""
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_deleted == False,
            )
        )
        notif = result.scalar_one_or_none()
        if not notif or notif.is_read:
            return notif

        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        await self.session.flush()
        return notif

    async def mark_all_read(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        """Bulk mark all unread as read. Returns count updated."""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc),
            )
            .returning(Notification.id)
        )
        return len(result.all())

    async def delete(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Soft-delete a notification (user removes it from inbox)."""
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if not notif:
            return False
        notif.is_deleted = True
        await self.session.flush()
        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_by_idempotency_key(self, key: str) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification).where(Notification.idempotency_key == key)
        )
        return result.scalar_one_or_none()
