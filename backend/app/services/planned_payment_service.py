"""PlannedPayment service."""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus, RecurrenceRule
from app.repositories.planned_payment import PlannedPaymentRepository
from app.schemas.planned_payment import PlannedPaymentCreate, PlannedPaymentUpdate
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, BusinessRuleError


class PlannedPaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PlannedPaymentRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: PlannedPaymentCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> List[PlannedPayment]:
        """
        Create planned payment(s).
        If recurrence_rule != NONE and recurrence_end_date is set,
        generates individual records for each occurrence up to recurrence_end_date.
        Returns list of all created records.
        """
        from dateutil.relativedelta import relativedelta

        rule = data.recurrence_rule
        end_date = data.recurrence_end_date

        # Build list of planned_dates to create
        dates_to_create: List[date] = []
        if rule != "NONE" and rule != RecurrenceRule.NONE and end_date:
            current = data.planned_date
            while current <= end_date:
                dates_to_create.append(current)
                if rule in ("DAILY", RecurrenceRule.DAILY):
                    current = current + relativedelta(days=1)
                elif rule in ("WEEKLY", RecurrenceRule.WEEKLY):
                    current = current + relativedelta(weeks=1)
                elif rule in ("MONTHLY", RecurrenceRule.MONTHLY):
                    current = current + relativedelta(months=1)
                elif rule in ("QUARTERLY", RecurrenceRule.QUARTERLY):
                    current = current + relativedelta(months=3)
                elif rule in ("YEARLY", RecurrenceRule.YEARLY):
                    current = current + relativedelta(years=1)
                else:
                    break
        else:
            dates_to_create = [data.planned_date]

        created: List[PlannedPayment] = []
        total = len(dates_to_create)
        for idx, planned_date in enumerate(dates_to_create, start=1):
            pp = PlannedPayment(
                tenant_id=tenant_id,
                group_id=data.group_id,
                payment_type=data.payment_type,
                title=data.title,
                amount=data.amount,
                currency=data.currency,
                account_id=data.account_id,
                category_id=data.category_id,
                planned_date=planned_date,
                due_date=data.due_date,
                reminder_date=data.reminder_date,
                recurrence_rule=data.recurrence_rule,
                recurrence_end_date=data.recurrence_end_date,
                total_installments=total if total > 1 else data.total_installments,
                current_installment=idx if total > 1 else data.total_installments,
                notes=data.notes,
            )
            pp = await self.repo.create(pp)
            created.append(pp)

        await self.audit.log(
            action="CREATE",
            module="planned_payments",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(created[0].id),
            after={"title": data.title, "amount": str(data.amount), "count": len(created)},
        )
        return created


    async def get_by_id(self, pp_id: uuid.UUID, tenant_id: uuid.UUID) -> PlannedPayment:
        pp = await self.repo.get_by_id_and_tenant(pp_id, tenant_id)
        if not pp:
            raise NotFoundError("PlannedPayment")
        return pp

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[PlannedPaymentStatus] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        offset: int = 0,
        limit: int = 50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[PlannedPayment], int]:
        return await self.repo.get_by_tenant(
            tenant_id, status=status, date_from=date_from, date_to=date_to,
            offset=offset, limit=limit, group_ids=group_ids,
        )

    async def mark_paid(
        self,
        pp_id: uuid.UUID,
        tenant_id: uuid.UUID,
        paid_amount: Optional[Decimal] = None,
        linked_transaction_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> PlannedPayment:
        """Mark a planned payment as paid (or partially paid)."""
        pp = await self.get_by_id(pp_id, tenant_id)
        if pp.status in (PlannedPaymentStatus.PAID, PlannedPaymentStatus.CANCELLED):
            raise BusinessRuleError(f"Cannot mark a {pp.status} payment as paid")

        amount_paid = paid_amount or pp.amount
        new_paid_total = (pp.paid_amount or Decimal("0")) + amount_paid

        if new_paid_total >= pp.amount:
            new_status = PlannedPaymentStatus.PAID
        else:
            new_status = PlannedPaymentStatus.PARTIALLY_PAID

        update_kwargs: dict = {
            "status": new_status,
            "paid_amount": new_paid_total,
        }
        if linked_transaction_id:
            update_kwargs["linked_transaction_id"] = linked_transaction_id

        pp = await self.repo.update(pp, **update_kwargs)
        await self.audit.log(
            action="MARK_PAID",
            module="planned_payments",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(pp_id),
            after={"status": new_status, "paid_amount": str(new_paid_total)},
        )
        return pp

    async def cancel(
        self,
        pp_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> PlannedPayment:
        pp = await self.get_by_id(pp_id, tenant_id)
        if pp.status == PlannedPaymentStatus.PAID:
            raise BusinessRuleError("Cannot cancel an already paid planned payment")

        pp = await self.repo.update(pp, status=PlannedPaymentStatus.CANCELLED)
        await self.audit.log(
            action="CANCEL",
            module="planned_payments",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(pp_id),
        )
        return pp

    async def update(
        self,
        pp_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: PlannedPaymentUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> PlannedPayment:
        pp = await self.get_by_id(pp_id, tenant_id)
        if pp.status == PlannedPaymentStatus.PAID:
            raise BusinessRuleError("Cannot edit a paid planned payment")

        update_fields = data.model_dump(exclude_none=True)
        pp = await self.repo.update(pp, **update_fields)
        await self.audit.log(
            action="UPDATE",
            module="planned_payments",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(pp_id),
            after=update_fields,
        )
        return pp

    async def flag_overdue(self, tenant_id: uuid.UUID) -> int:
        """Mark all overdue planned payments. Returns count updated."""
        today = datetime.now(timezone.utc).date()
        overdue_items = await self.repo.get_overdue(tenant_id, today)
        count = 0
        for pp in overdue_items:
            await self.repo.update(pp, status=PlannedPaymentStatus.OVERDUE)
            count += 1
        return count
