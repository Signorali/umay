"""
DemoSession Repository — data access for demo data tracking.

Tracks which demo records have been seeded per tenant,
enabling safe and complete cleanup without touching real data.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demo import DemoSession


class DemoSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[DemoSession]:
        return await self.session.get(DemoSession, session_id)

    async def get_active(self, tenant_id: uuid.UUID) -> Optional[DemoSession]:
        """Get the currently active demo session for a tenant (if any)."""
        result = await self.session.execute(
            select(DemoSession).where(
                DemoSession.tenant_id == tenant_id,
                DemoSession.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(
        self, tenant_id: uuid.UUID, limit: int = 20
    ) -> List[DemoSession]:
        result = await self.session.execute(
            select(DemoSession)
            .where(DemoSession.tenant_id == tenant_id)
            .order_by(DemoSession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def has_active_demo(self, tenant_id: uuid.UUID) -> bool:
        """Quick check whether demo data is currently seeded."""
        session = await self.get_active(tenant_id)
        return session is not None

    async def add(self, demo_session: DemoSession) -> DemoSession:
        self.session.add(demo_session)
        await self.session.flush()
        await self.session.refresh(demo_session)
        return demo_session

    async def deactivate(self, demo_session: DemoSession) -> DemoSession:
        """Mark demo session as ended (call after cleanup)."""
        from datetime import datetime, timezone
        demo_session.is_active = False
        demo_session.ended_at = datetime.now(timezone.utc)
        await self.session.flush()
        return demo_session

    async def update_seed_records(
        self,
        demo_session: DemoSession,
        seed_record_ids: dict,
        seeded_modules: Optional[str] = None,
    ) -> DemoSession:
        """Update the tracked seed record IDs after seeding completes."""
        demo_session.seed_record_ids = seed_record_ids
        if seeded_modules:
            demo_session.seeded_modules = seeded_modules
        await self.session.flush()
        return demo_session
