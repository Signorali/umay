"""Ledger repository — append-only, never update ledger entries."""
import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import LedgerEntry, EntryType


class LedgerRepository:
    """
    Ledger entries are append-only.
    No soft-delete, no update. Corrections via reversal transactions only.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entry: LedgerEntry) -> LedgerEntry:
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def create_many(self, entries: List[LedgerEntry]) -> List[LedgerEntry]:
        for entry in entries:
            self.session.add(entry)
        await self.session.flush()
        for entry in entries:
            await self.session.refresh(entry)
        return entries

    async def get_by_transaction(self, transaction_id: uuid.UUID) -> List[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry).where(LedgerEntry.transaction_id == transaction_id)
        )
        return list(result.scalars().all())

    async def get_account_balance(self, account_id: uuid.UUID) -> Decimal:
        """
        Calculate account balance from ledger entries.
        Balance = sum(DEBIT) - sum(CREDIT) for the account.
        Convention: DEBIT increases asset accounts, CREDIT decreases.
        """
        debit_result = await self.session.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.account_id == account_id,
                LedgerEntry.entry_type == EntryType.DEBIT,
            )
        )
        credit_result = await self.session.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.account_id == account_id,
                LedgerEntry.entry_type == EntryType.CREDIT,
            )
        )
        debit_total = debit_result.scalar_one() or Decimal("0")
        credit_total = credit_result.scalar_one() or Decimal("0")
        return Decimal(str(debit_total)) - Decimal(str(credit_total))

    async def verify_transaction_balance(self, transaction_id: uuid.UUID) -> bool:
        """
        Verify that ledger entries for a transaction are balanced:
        sum(DEBIT) == sum(CREDIT).
        """
        result = await self.session.execute(
            select(
                LedgerEntry.entry_type,
                func.sum(LedgerEntry.amount).label("total"),
            )
            .where(LedgerEntry.transaction_id == transaction_id)
            .group_by(LedgerEntry.entry_type)
        )
        rows = result.all()
        totals = {row.entry_type: Decimal(str(row.total)) for row in rows}
        debit = totals.get(EntryType.DEBIT, Decimal("0"))
        credit = totals.get(EntryType.CREDIT, Decimal("0"))
        return debit == credit
