"""
Notification Repository — data access for in-app notifications.
Only read/query operations live here. Writes remain in NotificationService
because they require idempotency-key deduplication logic.
"""
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationPriority


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Reads ─────────────────────────────────────────────────────────────────

    async def get_by_id(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        priority: Optional[NotificationPriority] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int]:
        """List notifications newest-first with pagination."""
        q = select(Notification).where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_deleted == False,
        )
        if unread_only:
            q = q.where(Notification.is_read == False)
        if notification_type:
            q = q.where(Notification.notification_type == notification_type)
        if priority:
            q = q.where(Notification.priority == priority)

        total = (
            await self.session.execute(
                select(func.count()).select_from(q.subquery())
            )
        ).scalar_one()

        items = (
            await self.session.execute(
                q.order_by(Notification.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()

        return list(items), total

    async def unread_count(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
        )
        return result.scalar_one()

    async def get_by_idempotency_key(self, key: str) -> Optional[Notification]:
        result = await self.session.execute(
            select(Notification).where(Notification.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Notification.tenant_id == tenant_id,
                Notification.is_deleted == False,
            )
        )
        return result.scalar_one()

    # ── Writes ────────────────────────────────────────────────────────────────

    async def add(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def bulk_mark_read(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> int:
        from datetime import datetime, timezone
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

    async def soft_delete(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
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
