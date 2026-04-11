"""
AuditLog Repository — query-only access to the immutable audit trail.

Design rules:
  - AuditLog records are NEVER updated or deleted.
  - This repo provides read/filter capabilities only.
  - Writes always go through AuditService.log().
"""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, log_id: uuid.UUID) -> Optional[AuditLog]:
        return await self.session.get(AuditLog, log_id)

    async def list(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        record_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AuditLog], int]:
        """Flexible audit log filter. All filters are optional, newest first."""
        filters = []
        if tenant_id:
            filters.append(AuditLog.tenant_id == tenant_id)
        if actor_id:
            filters.append(AuditLog.actor_id == actor_id)
        if module:
            filters.append(AuditLog.module == module)
        if action:
            filters.append(AuditLog.action == action)
        if record_id:
            filters.append(AuditLog.record_id == record_id)
        if date_from:
            filters.append(AuditLog.created_at >= date_from)
        if date_to:
            filters.append(AuditLog.created_at <= date_to)

        q = select(AuditLog)
        if filters:
            q = q.where(and_(*filters))

        total = (
            await self.session.execute(
                select(func.count()).select_from(q.subquery())
            )
        ).scalar_one()

        items = (
            await self.session.execute(
                q.order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()

        return list(items), total

    async def list_for_record(
        self,
        module: str,
        record_id: str,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get full history for a specific record."""
        filters = [
            AuditLog.module == module,
            AuditLog.record_id == record_id,
        ]
        if tenant_id:
            filters.append(AuditLog.tenant_id == tenant_id)

        result = await self.session.execute(
            select(AuditLog)
            .where(and_(*filters))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_actor(
        self,
        actor_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> int:
        filters = [AuditLog.actor_id == actor_id]
        if tenant_id:
            filters.append(AuditLog.tenant_id == tenant_id)
        result = await self.session.execute(
            select(func.count()).where(and_(*filters))
        )
        return result.scalar_one()

    async def list_security_events(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> List[AuditLog]:
        """High-urgency security events: LOGIN_FAILED, PERMISSION_CHANGED, etc."""
        security_actions = {
            "LOGIN_FAILED", "LOGIN", "LOGOUT", "PASSWORD_CHANGE",
            "PERMISSION_CHANGED", "ROLE_ASSIGNED", "PERIOD_LOCK",
            "PERIOD_UNLOCK", "FACTORY_RESET", "LICENSE_ACTIVATED",
        }
        q = select(AuditLog).where(
            AuditLog.action.in_(security_actions)
        )
        if tenant_id:
            q = q.where(AuditLog.tenant_id == tenant_id)

        result = await self.session.execute(
            q.order_by(AuditLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
