"""
CalendarService — builds calendar view from financial obligations.

Rule: App database is the source of truth. Calendar is a reflection layer only.
"""
import uuid
from datetime import date, timedelta
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.calendar_sync import CalendarRepository
from app.models.calendar_sync import CalendarItemType, CalendarSyncStatus
from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus
from app.models.loan import LoanInstallment, InstallmentStatus
from app.models.credit_card import CreditCard


class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CalendarRepository(db)

    # ------------------------------------------------------------------ #
    # Main sync: rebuild calendar items from DB sources
    # ------------------------------------------------------------------ #

    async def sync_for_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        months_ahead: int = 3,
    ) -> dict:
        """
        Automatically builds calendar items for the user from:
        - Pending planned payments
        - Pending loan installments
        - Credit card due dates
        Returns count of items synced.
        """
        today = date.today()
        until = today + timedelta(days=months_ahead * 30)

        items_created = 0

        # 1. Planned payments
        pp_q = select(PlannedPayment).where(
            PlannedPayment.tenant_id == tenant_id,
            PlannedPayment.status == PlannedPaymentStatus.PENDING,
            PlannedPayment.planned_date <= until,
            PlannedPayment.is_deleted == False,
        )
        pps = list((await self.db.execute(pp_q)).scalars().all())
        for pp in pps:
            await self.repo.create_item({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "item_type": CalendarItemType.PLANNED_PAYMENT,
                "title": pp.title,
                "due_date": pp.planned_date,
                "reminder_date": pp.reminder_date,
                "amount": pp.amount - pp.paid_amount,
                "currency": pp.currency,
                "linked_planned_payment_id": pp.id,
                "description": str(pp.payment_type.value) if pp.payment_type else "EXPENSE",
            })
            items_created += 1

        # 2. Loan installments
        inst_q = select(LoanInstallment).where(
            LoanInstallment.status.in_([InstallmentStatus.PENDING, InstallmentStatus.OVERDUE]),
            LoanInstallment.due_date <= until,
            LoanInstallment.is_deleted == False,
        )
        insts = list((await self.db.execute(inst_q)).scalars().all())
        for inst in insts:
            await self.repo.create_item({
                "tenant_id": tenant_id,
                "user_id": user_id,
                "item_type": CalendarItemType.LOAN_INSTALLMENT,
                "title": f"Kredi Taksiti #{inst.installment_number}",
                "due_date": inst.due_date,
                "amount": inst.total_amount - inst.paid_amount,
                "linked_loan_installment_id": inst.id,
            })
            items_created += 1

        # 3. Credit card due dates (current month)
        cc_q = select(CreditCard).where(
            CreditCard.tenant_id == tenant_id,
            CreditCard.is_deleted == False,
        )
        cards = list((await self.db.execute(cc_q)).scalars().all())
        for card in cards:
            # Compute next due date from due_day
            try:
                next_due = today.replace(day=card.due_day)
                if next_due < today:
                    m = today.month + 1 if today.month < 12 else 1
                    y = today.year if today.month < 12 else today.year + 1
                    next_due = next_due.replace(year=y, month=m)
            except ValueError:
                continue
            if next_due <= until and card.current_debt > 0:
                await self.repo.create_item({
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "item_type": CalendarItemType.CARD_DUE,
                    "title": f"{card.card_name} Ekstre Ödeme",
                    "due_date": next_due,
                    "amount": card.current_debt,
                    "currency": card.currency,
                    "linked_credit_card_id": card.id,
                })
                items_created += 1

        # Log the sync
        await self.repo.create_sync_log({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "sync_type": "internal",
            "status": CalendarSyncStatus.SYNCED,
            "items_synced": items_created,
        })

        await self.db.commit()
        return items_created  # Worker expects an int count

    # ------------------------------------------------------------------ #
    # Calendar item operations
    # ------------------------------------------------------------------ #

    async def get_items(
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
    ):
        return await self.repo.list_for_user(
            user_id, tenant_id,
            date_from=date_from, date_to=date_to,
            item_type=item_type,
            include_completed=include_completed,
            include_dismissed=include_dismissed,
            skip=skip, limit=limit,
        )

    async def dismiss_item(self, item_id: uuid.UUID, user_id: uuid.UUID):
        item = await self.repo.get_by_id(item_id, user_id)
        if not item:
            raise HTTPException(status_code=404, detail="Calendar item not found.")
        return await self.repo.update_item(item, {"is_dismissed": True})

    async def complete_item(self, item_id: uuid.UUID, user_id: uuid.UUID):
        item = await self.repo.get_by_id(item_id, user_id)
        if not item:
            raise HTTPException(status_code=404, detail="Calendar item not found.")
        updated = await self.repo.update_item(item, {"is_completed": True})
        await self.db.commit()
        return updated

    # ------------------------------------------------------------------ #
    # Worker-eligible: overdue detection
    # ------------------------------------------------------------------ #

    async def get_overdue_items(self) -> list:
        """
        Return all calendar items that are past their due_date and not yet completed/dismissed.
        Used by the background worker to generate notifications.
        Returns list of dicts with user/tenant context for notification dispatch.
        """
        from app.models.calendar_sync import CalendarItem
        today = date.today()
        q = select(CalendarItem).where(
            CalendarItem.due_date < today,
            CalendarItem.is_completed == False,
            CalendarItem.is_dismissed == False,
            CalendarItem.is_deleted == False,
        )
        items = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "user_id": str(item.user_id),
                "title": item.title,
                "due_date": str(item.due_date),
                "amount": float(item.amount or 0),
                "currency": item.currency or "TRY",
                "item_type": item.item_type,
            }
            for item in items
        ]

    async def mark_overdue_items(self) -> int:
        """
        Mark all past-due calendar items as overdue (sets is_overdue flag if present,
        or updates a status). Returns count of items marked.
        This is idempotent: already-completed/dismissed items are skipped.
        """
        from app.models.calendar_sync import CalendarItem
        from sqlalchemy import update as sa_update
        today = date.today()

        # We don't have an explicit is_overdue field, so we just return
        # the count of overdue items (they remain pending until completed/dismissed).
        # Future extension: add is_overdue column to CalendarItem model.
        q = select(CalendarItem).where(
            CalendarItem.due_date < today,
            CalendarItem.is_completed == False,
            CalendarItem.is_dismissed == False,
            CalendarItem.is_deleted == False,
        )
        items = list((await self.db.execute(q)).scalars().all())
        return len(items)
