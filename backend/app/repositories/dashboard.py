"""Dashboard widget repository."""
import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dashboard import DashboardWidget


class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_widgets(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[DashboardWidget]:
        q = select(DashboardWidget).where(
            DashboardWidget.user_id == user_id,
            DashboardWidget.tenant_id == tenant_id,
            DashboardWidget.is_deleted == False,
            DashboardWidget.is_visible == True,
        ).order_by(DashboardWidget.position)
        return list((await self.db.execute(q)).scalars().all())

    async def get_by_id(self, widget_id: uuid.UUID, user_id: uuid.UUID) -> Optional[DashboardWidget]:
        q = select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.user_id == user_id,
            DashboardWidget.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> DashboardWidget:
        obj = DashboardWidget(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, widget: DashboardWidget, data: dict) -> DashboardWidget:
        for k, v in data.items():
            setattr(widget, k, v)
        await self.db.flush()
        await self.db.refresh(widget)
        return widget

    async def delete(self, widget: DashboardWidget) -> None:
        widget.is_deleted = True
        await self.db.flush()

    async def bulk_upsert_defaults(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, widget_defs: List[dict]
    ) -> List[DashboardWidget]:
        """Create default widgets if user has none."""
        existing = await self.get_user_widgets(user_id, tenant_id)
        if existing:
            return existing
        objs = [
            DashboardWidget(tenant_id=tenant_id, user_id=user_id, **w)
            for w in widget_defs
        ]
        self.db.add_all(objs)
        await self.db.flush()
        return objs
