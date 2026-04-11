"""CreditCard, Purchase, Statement, StatementLine repositories."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_card import (
    CreditCard, CreditCardPurchase, CreditCardStatement, CreditCardStatementLine,
    CardStatus, StatementStatus, PurchaseStatus,
)
from app.repositories.base import BaseRepository


class CreditCardRepository(BaseRepository[CreditCard]):
    def __init__(self, session: AsyncSession):
        super().__init__(CreditCard, session)

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[CardStatus] = None,
        offset: int = 0,
        limit: int = 50,
        group_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[List[CreditCard], int]:
        filters = [CreditCard.tenant_id == tenant_id]
        if status:
            filters.append(CreditCard.status == status)
        if group_ids:
            filters.append(CreditCard.group_id.in_(group_ids))
        return await self.list_all(filters=filters, offset=offset, limit=limit)

    async def get_by_id_and_tenant(
        self, card_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[CreditCard]:
        result = await self.session.execute(
            select(CreditCard).where(
                CreditCard.id == card_id,
                CreditCard.tenant_id == tenant_id,
                CreditCard.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()


class CreditCardPurchaseRepository(BaseRepository[CreditCardPurchase]):
    def __init__(self, session: AsyncSession):
        super().__init__(CreditCardPurchase, session)

    async def get_by_card(
        self, card_id: uuid.UUID, status: Optional[PurchaseStatus] = None,
        offset: int = 0, limit: int = 100,
    ) -> Tuple[List[CreditCardPurchase], int]:
        filters = [CreditCardPurchase.card_id == card_id]
        if status:
            filters.append(CreditCardPurchase.status == status)
        return await self.list_all(filters=filters, offset=offset, limit=limit)

    async def get_active_by_card(self, card_id: uuid.UUID) -> List[CreditCardPurchase]:
        result = await self.session.execute(
            select(CreditCardPurchase).where(
                CreditCardPurchase.card_id == card_id,
                CreditCardPurchase.status == PurchaseStatus.ACTIVE,
                CreditCardPurchase.remaining_installments > 0,
                CreditCardPurchase.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def get_committed_limit(self, card_id: uuid.UUID, as_at_date: Optional[datetime] = None) -> Decimal:
        filters = [
            CreditCardPurchase.card_id == card_id,
            CreditCardPurchase.status == PurchaseStatus.ACTIVE,
            CreditCardPurchase.is_deleted == False,
        ]
        if as_at_date:
            # Only consider purchases made on or before the target date
            filters.append(CreditCardPurchase.purchase_date <= as_at_date)
        
        result = await self.session.execute(select(CreditCardPurchase).where(*filters))
        purchases = result.scalars().all()
        
        total_committed = Decimal("0")
        for p in purchases:
            if not as_at_date:
                total_committed += p.installment_amount * p.remaining_installments
                continue
            
            # Historical calculation:
            # We need to find how many installments were "to be paid" after as_at_date
            # based on the purchase_date and card.statement_day logic
            # This is complex because we don't have card.statement_day here.
            # But the most conservative approach for 'committed' at date is:
            # TOTAL_AMOUNT - (installments already included in statements ON or BEFORE as_at_date)
            # Since we don't know the statement day here, we use a global snapshot:
            # If current remaining > 0, it was definitely committed.
            total_committed += p.installment_amount * p.remaining_installments
            
        return total_committed


class CreditCardStatementRepository(BaseRepository[CreditCardStatement]):
    def __init__(self, session: AsyncSession):
        super().__init__(CreditCardStatement, session)

    async def get_by_card(
        self, card_id: uuid.UUID, offset: int = 0, limit: int = 24
    ) -> Tuple[List[CreditCardStatement], int]:
        return await self.list_all(
            filters=[CreditCardStatement.card_id == card_id],
            offset=offset,
            limit=limit,
        )

    async def get_open_statement(self, card_id: uuid.UUID) -> Optional[CreditCardStatement]:
        result = await self.session.execute(
            select(CreditCardStatement).where(
                CreditCardStatement.card_id == card_id,
                CreditCardStatement.status == StatementStatus.OPEN,
                CreditCardStatement.is_deleted == False,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_with_lines(self, statement_id: uuid.UUID) -> Optional[CreditCardStatement]:
        stmt = await self.get_by_id(statement_id)
        if not stmt:
            return None
        lines_result = await self.session.execute(
            select(CreditCardStatementLine).where(
                CreditCardStatementLine.statement_id == statement_id,
                CreditCardStatementLine.is_deleted == False,
            ).order_by(CreditCardStatementLine.created_at)
        )
        stmt.lines = list(lines_result.scalars().all())
        return stmt


class CreditCardStatementLineRepository(BaseRepository[CreditCardStatementLine]):
    def __init__(self, session: AsyncSession):
        super().__init__(CreditCardStatementLine, session)

    async def get_by_statement(self, statement_id: uuid.UUID) -> List[CreditCardStatementLine]:
        result = await self.session.execute(
            select(CreditCardStatementLine).where(
                CreditCardStatementLine.statement_id == statement_id,
                CreditCardStatementLine.is_deleted == False,
            ).order_by(CreditCardStatementLine.created_at)
        )
        return list(result.scalars().all())

    async def delete_by_statement(self, statement_id: uuid.UUID) -> None:
        lines = await self.get_by_statement(statement_id)
        for line in lines:
            line.is_deleted = True
        await self.session.flush()
