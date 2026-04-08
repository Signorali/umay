"""PlannedPayment repository."""
import uuid
from datetime import date
from typing import List, Optional, Tuple, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus
from app.repositories.base import BaseRepository


class PlannedPaymentRepository(BaseRepository[PlannedPayment]):
    def __init__(self, session: AsyncSession):
        super().__init__(PlannedPayment, session)

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[PlannedPaymentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        offset: int = 0,
        limit: int = 50,
        group_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[List[PlannedPayment], int]:
        query = select(PlannedPayment).where(PlannedPayment.is_deleted == False)
        filters = [PlannedPayment.tenant_id == tenant_id]
        if status:
            filters.append(PlannedPayment.status == status)
        if date_from:
            filters.append(PlannedPayment.planned_date >= date_from)
        if date_to:
            filters.append(PlannedPayment.planned_date <= date_to)
        if group_ids:
            filters.append(PlannedPayment.group_id.in_(group_ids))
        query = query.where(*filters)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        query = query.order_by(PlannedPayment.planned_date.asc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id_and_tenant(
        self, pp_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[PlannedPayment]:
        result = await self.session.execute(
            select(PlannedPayment).where(
                PlannedPayment.id == pp_id,
                PlannedPayment.tenant_id == tenant_id,
                PlannedPayment.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_overdue(self, tenant_id: uuid.UUID, as_of: date) -> List[PlannedPayment]:
        result = await self.session.execute(
            select(PlannedPayment).where(
                PlannedPayment.tenant_id == tenant_id,
                PlannedPayment.status == PlannedPaymentStatus.PENDING,
                PlannedPayment.due_date < as_of,
                PlannedPayment.is_deleted == False,
            )
        )
        return list(result.scalars().all())
