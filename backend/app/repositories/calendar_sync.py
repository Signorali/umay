"""Calendar sync repository."""
import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_sync import CalendarItem, CalendarSyncLog, CalendarItemType


class CalendarRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_item(self, data: dict) -> CalendarItem:
        obj = CalendarItem(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def bulk_create_items(self, items: List[dict]) -> List[CalendarItem]:
        objs = [CalendarItem(**i) for i in items]
        self.db.add_all(objs)
        await self.db.flush()
        return objs

    async def get_by_id(self, item_id: uuid.UUID, user_id: uuid.UUID) -> Optional[CalendarItem]:
        q = select(CalendarItem).where(
            CalendarItem.id == item_id,
            CalendarItem.user_id == user_id,
            CalendarItem.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        item_type: Optional[str] = None,
        include_completed: bool = False,
        include_dismissed: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CalendarItem]:
        q = select(CalendarItem).where(
            CalendarItem.user_id == user_id,
            CalendarItem.tenant_id == tenant_id,
            CalendarItem.is_deleted == False,
        )
        if not include_completed:
            q = q.where(CalendarItem.is_completed == False)
        if not include_dismissed:
            q = q.where(CalendarItem.is_dismissed == False)
        if date_from:
            q = q.where(CalendarItem.due_date >= date_from)
        if date_to:
            q = q.where(CalendarItem.due_date <= date_to)
        if item_type:
            q = q.where(CalendarItem.item_type == item_type)
        q = q.order_by(CalendarItem.due_date).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def update_item(self, item: CalendarItem, data: dict) -> CalendarItem:
        for k, v in data.items():
            setattr(item, k, v)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete_by_source(
        self,
        linked_planned_payment_id: Optional[uuid.UUID] = None,
        linked_loan_installment_id: Optional[uuid.UUID] = None,
        linked_credit_card_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Remove stale calendar items when source is deleted."""
        q = select(CalendarItem).where(CalendarItem.is_deleted == False)
        if linked_planned_payment_id:
            q = q.where(CalendarItem.linked_planned_payment_id == linked_planned_payment_id)
        elif linked_loan_installment_id:
            q = q.where(CalendarItem.linked_loan_installment_id == linked_loan_installment_id)
        elif linked_credit_card_id:
            q = q.where(CalendarItem.linked_credit_card_id == linked_credit_card_id)
        items = list((await self.db.execute(q)).scalars().all())
        for item in items:
            item.is_deleted = True
        await self.db.flush()
        return len(items)

    async def create_sync_log(self, data: dict) -> CalendarSyncLog:
        obj = CalendarSyncLog(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
