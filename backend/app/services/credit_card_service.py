"""CreditCard service — card, purchase, statement, payment, refund management."""
import uuid
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_card import (
    CreditCard, CreditCardPurchase, CreditCardStatement, CreditCardStatementLine,
    CardStatus, StatementStatus, PurchaseStatus, StatementLineType,
)
from app.models.planned_payment import PlannedPayment, PlannedPaymentType, PlannedPaymentStatus, RecurrenceRule
from app.repositories.credit_card import (
    CreditCardRepository, CreditCardPurchaseRepository,
    CreditCardStatementRepository, CreditCardStatementLineRepository,
)
from app.schemas.credit_card import (
    CreditCardCreate, CreditCardUpdate,
    PurchaseCreate, StatementGenerateRequest, StatementDetailRequest,
    StatementPayRequest, CancelPurchaseRequest, StatementCreateRequest,
)
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, BusinessRuleError, ConflictError


class CreditCardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CreditCardRepository(session)
        self.purchase_repo = CreditCardPurchaseRepository(session)
        self.statement_repo = CreditCardStatementRepository(session)
        self.line_repo = CreditCardStatementLineRepository(session)
        self.audit = AuditService(session)

    # ── Card CRUD ───────────────────────────────────────

    async def create(
        self, tenant_id: uuid.UUID, data: CreditCardCreate,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCard:
        if not (1 <= data.statement_day <= 31):
            raise BusinessRuleError("Statement day must be between 1 and 31")
        if not (1 <= data.due_day <= 31):
            raise BusinessRuleError("Due day must be between 1 and 31")

        card = CreditCard(
            tenant_id=tenant_id, group_id=data.group_id,
            card_name=data.card_name, bank_name=data.bank_name,
            card_type=data.card_type, network=data.network,
            last_four_digits=data.last_four_digits,
            credit_limit=data.credit_limit, currency=data.currency,
            statement_day=data.statement_day, due_day=data.due_day,
            account_id=data.account_id, payment_account_id=data.payment_account_id,
            expiry_month=data.expiry_month, expiry_year=data.expiry_year,
            notes=data.notes,
        )
        card = await self.repo.create(card)
        await self.audit.log(
            action="CREATE", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(card.id),
            after={"name": card.card_name, "bank": card.bank_name, "limit": str(card.credit_limit)},
        )
        return card

    async def get_by_id(self, card_id: uuid.UUID, tenant_id: uuid.UUID) -> CreditCard:
        card = await self.repo.get_by_id_and_tenant(card_id, tenant_id)
        if not card:
            raise NotFoundError("CreditCard")
        return card

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[CreditCard], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit, group_ids=group_ids)

    async def update(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID, data: CreditCardUpdate,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCard:
        card = await self.get_by_id(card_id, tenant_id)
        update_fields = data.model_dump(exclude_none=True)
        card = await self.repo.update(card, **update_fields)
        await self.audit.log(
            action="UPDATE", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(card_id), after=update_fields,
        )
        return card

    # ── Limits ──────────────────────────────────────────

    async def get_limits(self, card_id: uuid.UUID, tenant_id: uuid.UUID, at_date: Optional[date] = None) -> dict:
        card = await self.get_by_id(card_id, tenant_id)
        
        # Convert date to datetime for repo if needed
        as_at = datetime.combine(at_date, datetime.min.time()) if at_date else None
        
        committed = await self.purchase_repo.get_committed_limit(card_id, as_at_date=as_at)
        theoretical_available = card.credit_limit - committed
        
        return {
            "card_id": card_id,
            "total_limit": card.credit_limit,
            "committed_limit": committed,
            "theoretical_available": theoretical_available,
            "current_debt": card.current_debt,
        }

    # ── Purchase (Installment) ──────────────────────────

    async def create_purchase(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID, data: PurchaseCreate,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardPurchase:
        card = await self.get_by_id(card_id, tenant_id)
        if card.status != CardStatus.ACTIVE:
            raise BusinessRuleError("Card is not active")

        installment_amount = data.total_amount / data.installment_count
        committed = await self.purchase_repo.get_committed_limit(card_id)
        theoretical_available = card.credit_limit - committed
        if data.total_amount > theoretical_available:
            raise BusinessRuleError(
                f"Insufficient available limit. Available: {theoretical_available}, Requested: {data.total_amount}"
            )

        purchase = CreditCardPurchase(
            tenant_id=tenant_id, card_id=card_id,
            group_id=data.group_id, category_id=data.category_id,
            description=data.description,
            total_amount=data.total_amount,
            installment_count=data.installment_count,
            installment_amount=installment_amount,
            currency=data.currency or card.currency,
            purchase_date=data.purchase_date,
            remaining_installments=data.installment_count,
            status=PurchaseStatus.ACTIVE,
        )
        purchase = await self.purchase_repo.create(purchase)

        # Update card debt
        card = await self.repo.update(card, current_debt=card.current_debt + data.total_amount)

        # Create planned payments for each installment
        current_date = data.purchase_date
        statement_day = card.statement_day
        # Find first statement period after purchase
        if current_date.day <= statement_day:
            first_month = current_date.replace(day=1)
        else:
            first_month = (current_date.replace(day=1) + relativedelta(months=1))

        for i in range(data.installment_count):
            installment_date = first_month + relativedelta(months=i)
            try:
                planned_date = installment_date.replace(day=card.due_day)
            except ValueError:
                import calendar
                last_day = calendar.monthrange(installment_date.year, installment_date.month)[1]
                planned_date = installment_date.replace(day=min(card.due_day, last_day))

            pp = PlannedPayment(
                tenant_id=tenant_id, group_id=data.group_id,
                payment_type=PlannedPaymentType.EXPENSE,
                status=PlannedPaymentStatus.PENDING,
                title=f"KK Taksit: {data.description} ({i+1}/{data.installment_count})",
                amount=installment_amount, currency=data.currency or card.currency,
                account_id=card.account_id, category_id=data.category_id,
                planned_date=planned_date,
                due_date=planned_date,
                recurrence_rule=RecurrenceRule.NONE,
                total_installments=data.installment_count,
                current_installment=i + 1,
                parent_planned_payment_id=None,
                credit_card_purchase_id=purchase.id,
                notes=f"Kredi kartı taksit - Alışveriş ID: {purchase.id}",
            )
            self.session.add(pp)

        await self.session.flush()

        await self.audit.log(
            action="CREATE_PURCHASE", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(purchase.id),
            after={
                "card_id": str(card_id), "description": data.description,
                "total": str(data.total_amount), "installments": data.installment_count,
            },
        )
        return purchase

    async def list_purchases(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID,
        status: Optional[PurchaseStatus] = None,
        offset: int = 0, limit: int = 100,
    ) -> Tuple[List[CreditCardPurchase], int]:
        await self.get_by_id(card_id, tenant_id)
        return await self.purchase_repo.get_by_card(card_id, status=status, offset=offset, limit=limit)

    # ── Statement Generation ────────────────────────────

    async def _calc_statement_figures(
        self, card_id: uuid.UUID, card, data
    ) -> dict:
        """Shared calculation logic for both preview and generate."""
        committed = await self.purchase_repo.get_committed_limit(card_id, as_at_date=data.period_end)
        theoretical_available = card.credit_limit - committed

        new_spending = theoretical_available - data.real_available_limit
        new_spending = new_spending.quantize(Decimal("0.0001"))
        if new_spending < Decimal("0"):
            new_spending = Decimal("0")

        active_purchases = await self.purchase_repo.get_active_by_card(card_id)
        installment_total = Decimal("0")
        installment_lines: list = []

        for purchase in active_purchases:
            # Skip purchases made after this period ends
            if purchase.purchase_date > data.period_end:
                continue

            # Installment number = which one is next based on how many remain
            # This is reliable regardless of whether period_end aligns with statement_day
            inst_number = purchase.installment_count - purchase.remaining_installments + 1

            if 1 <= inst_number <= purchase.installment_count:
                installment_lines.append({
                    "purchase_id": purchase.id,
                    "group_id": purchase.group_id,
                    "category_id": purchase.category_id,
                    "description": purchase.description,
                    "amount": purchase.installment_amount,
                    "installment_number": inst_number,
                    "total_installments": purchase.installment_count,
                })
                installment_total += purchase.installment_amount

        future_committed = committed - installment_total
        total_spending = installment_total + new_spending

        return {
            "committed": committed,
            "theoretical_available": theoretical_available,
            "new_spending": new_spending,
            "installment_total": installment_total,
            "future_committed": future_committed,
            "total_spending": total_spending,
            "installment_lines": installment_lines,
        }

    async def preview_statement(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID, data,
    ) -> dict:
        """Dry-run: calculate statement figures without saving."""
        card = await self.get_by_id(card_id, tenant_id)
        figs = await self._calc_statement_figures(card_id, card, data)
        return {
            "total_limit": float(card.credit_limit),
            "future_committed": float(figs["future_committed"]),
            "real_available": float(data.real_available_limit),
            "installment_total": float(figs["installment_total"]),
            "new_spending": float(figs["new_spending"]),
            "total_spending": float(figs["total_spending"]),
        }

    async def generate_statement(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID, data: StatementGenerateRequest,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        card = await self.get_by_id(card_id, tenant_id)

        # Check no open statement exists
        existing = await self.statement_repo.get_open_statement(card_id)
        if existing:
            raise ConflictError("Card already has an open statement. Finalize or delete it first.")

        figs = await self._calc_statement_figures(card_id, card, data)
        committed = figs["committed"]
        theoretical_available = figs["theoretical_available"]
        new_spending = figs["new_spending"]
        installment_total = figs["installment_total"]
        installment_lines = figs["installment_lines"]
        total_spending = figs["total_spending"]

        # Calculate due_date from card.due_day and period_end
        due_month = data.period_end + relativedelta(months=1)
        try:
            due_date = due_month.replace(day=card.due_day)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(due_month.year, due_month.month)[1]
            due_date = due_month.replace(day=min(card.due_day, last_day))

        statement = CreditCardStatement(
            card_id=card_id,
            status=StatementStatus.OPEN,
            period_start=data.period_start,
            period_end=data.period_end,
            statement_closing_date=data.period_end,
            due_date=due_date,
            total_spending=total_spending,
            minimum_payment=total_spending,
            theoretical_available=theoretical_available,
            real_available=data.real_available_limit,
            new_spending=new_spending,
        )
        statement = await self.statement_repo.create(statement)

        # Create installment lines
        for line_data in installment_lines:
            line = CreditCardStatementLine(
                statement_id=statement.id,
                purchase_id=line_data["purchase_id"],
                group_id=line_data["group_id"],
                category_id=line_data["category_id"],
                line_type=StatementLineType.INSTALLMENT.value,
                description=line_data["description"],
                amount=line_data["amount"],
                installment_number=line_data["installment_number"],
                total_installments=line_data["total_installments"],
            )
            self.session.add(line)

        # If new spending > 0, create a single NEW_SPENDING line (user can detail later)
        if new_spending > Decimal("0"):
            new_line = CreditCardStatementLine(
                statement_id=statement.id,
                line_type=StatementLineType.NEW_SPENDING.value,
                description="Yeni harcamalar",
                amount=new_spending,
                group_id=card.group_id,
            )
            self.session.add(new_line)

        await self.session.flush()

        await self.audit.log(
            action="GENERATE_STATEMENT", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(statement.id),
            after={"total": str(total_spending), "new_spending": str(new_spending)},
        )
        return statement

    # ── Statement Detail (breakdown of new spending) ────

    async def detail_new_spending(
        self, card_id: uuid.UUID, statement_id: uuid.UUID,
        tenant_id: uuid.UUID, data: StatementDetailRequest,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        card = await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        status_val = getattr(statement.status, "value", str(statement.status))
        if status_val != StatementStatus.OPEN.value:
            raise BusinessRuleError("Only OPEN statements can be detailed")

        total_detail = sum(Decimal(str(line.amount)) for line in data.lines).quantize(Decimal("0.01"))
        db_new_spending = Decimal(str(statement.new_spending)).quantize(Decimal("0.01"))
        if total_detail > db_new_spending + Decimal("0.01"):
            raise BusinessRuleError(
                f"Detay toplamı ({total_detail}) harcama tutarını ({db_new_spending}) aşamaz"
            )

        existing_lines = await self.line_repo.get_by_statement(statement_id)
        target_type = StatementLineType.NEW_SPENDING.value
        for eline in existing_lines:
            etype = getattr(eline.line_type, "value", str(eline.line_type))
            if etype == target_type:
                eline.is_deleted = True

        # Create detailed lines
        for line_input in data.lines:
            line = CreditCardStatementLine(
                statement_id=statement_id,
                line_type=StatementLineType.NEW_SPENDING.value,
                group_id=card.group_id,
                category_id=line_input.category_id,
                description=line_input.description,
                amount=line_input.amount,
            )
            self.session.add(line)

        # If there's remaining undetailed amount, keep a catch-all line
        remainder = db_new_spending - total_detail
        if remainder > Decimal("0.01"):
            remainder_line = CreditCardStatementLine(
                statement_id=statement_id,
                line_type=StatementLineType.NEW_SPENDING.value,
                group_id=card.group_id,
                description="Diğer harcamalar",
                amount=remainder,
            )
            self.session.add(remainder_line)

        await self.session.flush()
        return statement

    # ── Statement Delete (only OPEN) ─────────────────────

    async def delete_statement(
        self, card_id: uuid.UUID, statement_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> None:
        card = await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        status_val = getattr(statement.status, "value", str(statement.status))
        if status_val != StatementStatus.OPEN.value:
            raise BusinessRuleError("Sadece açık (kesinleşmemiş) ekstreler silinebilir")

        # Soft-delete all lines
        lines = await self.line_repo.get_by_statement(statement_id)
        for line in lines:
            line.is_deleted = True

        # Soft-delete statement
        statement.is_deleted = True
        await self.session.flush()

        await self.audit.log(
            action="DELETE_STATEMENT", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(statement_id),
        )

    # ── Statement Finalize ──────────────────────────────

    async def finalize_statement(
        self, card_id: uuid.UUID, statement_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        card = await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        finalize_status = getattr(statement.status, "value", str(statement.status))
        if finalize_status != StatementStatus.OPEN.value:
            raise BusinessRuleError("Only OPEN statements can be finalized")

        # Mark related planned payments as PAID for installment lines
        lines = await self.line_repo.get_by_statement(statement_id)
        for line in lines:
            line_type_val = getattr(line.line_type, "value", str(line.line_type))
            if line_type_val == StatementLineType.INSTALLMENT.value and line.purchase_id:
                purchase = await self.purchase_repo.get_by_id(line.purchase_id)
                if purchase and purchase.remaining_installments > 0:
                    await self.purchase_repo.update(
                        purchase, remaining_installments=purchase.remaining_installments - 1
                    )

                # Mark corresponding planned payment as PAID
                pp_result = await self.session.execute(
                    select(PlannedPayment).where(
                        PlannedPayment.notes.contains(str(line.purchase_id)),
                        PlannedPayment.current_installment == line.installment_number,
                        PlannedPayment.status == PlannedPaymentStatus.PENDING,
                        PlannedPayment.is_deleted == False,
                    ).limit(1)
                )
                pp = pp_result.scalar_one_or_none()
                if pp:
                    pp.status = PlannedPaymentStatus.PAID
                    pp.paid_amount = pp.amount

        statement = await self.statement_repo.update(statement, status=StatementStatus.CLOSED)

        await self.audit.log(
            action="FINALIZE_STATEMENT", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(statement_id),
        )
        return statement

    # ── Statement Payment ───────────────────────────────

    async def pay_statement(
        self, card_id: uuid.UUID, statement_id: uuid.UUID,
        tenant_id: uuid.UUID, data: StatementPayRequest,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        from app.services.transaction_service import TransactionService
        from app.schemas.transaction import TransactionCreate
        from app.models.transaction import TransactionType, TransactionStatus

        card = await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        pay_status = getattr(statement.status, "value", str(statement.status))
        if pay_status == StatementStatus.PAID.value:
            raise BusinessRuleError("Statement is already paid")
        if pay_status == StatementStatus.OPEN.value:
            raise BusinessRuleError("Statement must be finalized before payment")

        # Create EXPENSE transaction from source account
        tx_svc = TransactionService(self.session)
        tx_data = TransactionCreate(
            transaction_type=TransactionType.EXPENSE,
            amount=data.amount,
            currency=card.currency,
            source_account_id=data.source_account_id,
            transaction_date=datetime.now(timezone.utc).date(),
            description=f"Kredi kartı ekstre ödemesi - {card.card_name} ({statement.period_start} → {statement.period_end})",
            status=TransactionStatus.CONFIRMED,
            system_generated=True,
        )
        tx = await tx_svc.create(
            tenant_id=tenant_id, group_id=card.group_id,
            data=tx_data, actor_id=actor_id, actor_email=actor_email,
        )

        # Update statement
        new_paid = (statement.paid_amount or Decimal("0")) + data.amount
        if new_paid >= statement.total_spending:
            new_status = StatementStatus.PAID
        else:
            new_status = StatementStatus.PARTIALLY_PAID

        statement = await self.statement_repo.update(
            statement,
            paid_amount=new_paid,
            status=new_status,
            payment_account_id=data.source_account_id,
            payment_date=datetime.now(timezone.utc).date(),
            payment_transaction_id=tx.id,
        )

        # Reduce card debt
        new_debt = card.current_debt - data.amount
        if new_debt < 0:
            new_debt = Decimal("0")
        await self.repo.update(card, current_debt=new_debt)

        await self.audit.log(
            action="PAY_STATEMENT", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(statement_id),
            after={"amount": str(data.amount), "tx_id": str(tx.id)},
        )
        return statement

    # ── Cancel / Refund Purchase ────────────────────────

    async def cancel_purchase(
        self, card_id: uuid.UUID, purchase_id: uuid.UUID,
        tenant_id: uuid.UUID, scenario: str,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardPurchase:
        card = await self.get_by_id(card_id, tenant_id)
        purchase = await self.purchase_repo.get_by_id(purchase_id)
        if not purchase or purchase.card_id != card_id:
            raise NotFoundError("Purchase")
        if purchase.status != PurchaseStatus.ACTIVE:
            raise BusinessRuleError("Only active purchases can be cancelled")

        if scenario == "A":
            # Scenario A: Full cancel — delete remaining installments
            remaining_amount = purchase.installment_amount * purchase.remaining_installments

            # Cancel planned payments
            pp_result = await self.session.execute(
                select(PlannedPayment).where(
                    PlannedPayment.notes.contains(str(purchase_id)),
                    PlannedPayment.status == PlannedPaymentStatus.PENDING,
                    PlannedPayment.is_deleted == False,
                )
            )
            pending_pps = list(pp_result.scalars().all())
            for pp in pending_pps:
                pp.status = PlannedPaymentStatus.CANCELLED

            # Update purchase
            purchase = await self.purchase_repo.update(
                purchase, status=PurchaseStatus.CANCELLED, remaining_installments=0
            )

            # Release committed limit from card debt
            new_debt = card.current_debt - remaining_amount
            if new_debt < 0:
                new_debt = Decimal("0")
            await self.repo.update(card, current_debt=new_debt)

        elif scenario == "B":
            # Scenario B: Installment-by-installment refund
            # Convert remaining planned payments to INCOME (refund)
            pp_result = await self.session.execute(
                select(PlannedPayment).where(
                    PlannedPayment.notes.contains(str(purchase_id)),
                    PlannedPayment.status == PlannedPaymentStatus.PENDING,
                    PlannedPayment.is_deleted == False,
                )
            )
            pending_pps = list(pp_result.scalars().all())
            for pp in pending_pps:
                pp.payment_type = PlannedPaymentType.INCOME
                pp.title = f"KK İade: {purchase.description} ({pp.current_installment}/{purchase.installment_count})"

            purchase = await self.purchase_repo.update(purchase, status=PurchaseStatus.REFUNDED)

        else:
            raise BusinessRuleError("Invalid scenario. Use 'A' or 'B'.")

        await self.session.flush()

        await self.audit.log(
            action=f"CANCEL_PURCHASE_{scenario}", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(purchase_id),
            after={"scenario": scenario, "purchase": purchase.description},
        )
        return purchase

    # ── Statement Listing ───────────────────────────────

    async def list_statements(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID,
        offset: int = 0, limit: int = 24,
    ) -> Tuple[List[CreditCardStatement], int]:
        await self.get_by_id(card_id, tenant_id)
        return await self.statement_repo.get_by_card(card_id, offset=offset, limit=limit)

    async def get_statement_detail(
        self, card_id: uuid.UUID, statement_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> CreditCardStatement:
        await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_with_lines(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        return statement

    # ── Legacy compat ──────────────────────────────────

    async def close_statement(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        return await self.finalize_statement(card_id, None, tenant_id, actor_id, actor_email)

    async def create_statement(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID, data: StatementCreateRequest,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        await self.get_by_id(card_id, tenant_id)
        existing_open = await self.statement_repo.get_open_statement(card_id)
        if existing_open:
            raise ConflictError("Card already has an open statement. Close it first.")
        statement = CreditCardStatement(
            card_id=card_id,
            period_start=data.period_start, period_end=data.period_end,
            due_date=data.due_date, status=StatementStatus.OPEN,
        )
        return await self.statement_repo.create(statement)

    async def record_payment(
        self, card_id: uuid.UUID, statement_id: uuid.UUID,
        tenant_id: uuid.UUID, amount: Decimal,
        actor_id: Optional[uuid.UUID] = None, actor_email: Optional[str] = None,
    ) -> CreditCardStatement:
        await self.get_by_id(card_id, tenant_id)
        statement = await self.statement_repo.get_by_id(statement_id)
        if not statement or statement.card_id != card_id:
            raise NotFoundError("Statement")
        new_paid = (statement.paid_amount or Decimal("0")) + amount
        if new_paid >= statement.total_spending:
            new_status = StatementStatus.PAID
        else:
            new_status = StatementStatus.PARTIALLY_PAID
        statement = await self.statement_repo.update(statement, paid_amount=new_paid, status=new_status)
        await self.audit.log(
            action="RECORD_PAYMENT", module="credit_cards",
            tenant_id=tenant_id, actor_id=actor_id, actor_email=actor_email,
            record_id=str(card_id),
            after={"statement_id": str(statement_id), "amount": str(amount)},
        )
        return statement
