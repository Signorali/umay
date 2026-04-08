"""
Ledger Service — Double-Entry Accounting Engine.

This is the core financial integrity enforcer of Umay.

Rules enforced here:
1. Every confirmed transaction MUST produce ledger entries
2. Ledger entries MUST be balanced: sum(DEBIT) == sum(CREDIT)
3. Ledger entries are NEVER updated or deleted
4. Corrections happen via reversal transactions only
5. Account balances are always derived from ledger totals

Posting convention:
  INCOME:
    DEBIT  target_account
    CREDIT system income offset account

  EXPENSE:
    DEBIT  system expense offset account
    CREDIT source_account

  TRANSFER:
    DEBIT  target_account
    CREDIT source_account

Important:
- ledger_entries.account_id is NOT NULL, so offset rows must use real system accounts
- system offset accounts are created automatically per tenant + currency
- system offset accounts are hidden from totals (include_in_total=False)
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import LedgerEntry, EntryType
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.account import Account, AccountType
from app.repositories.ledger import LedgerRepository
from app.repositories.account import AccountRepository
from app.core.exceptions import BusinessRuleError


class LedgerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger_repo = LedgerRepository(session)
        self.account_repo = AccountRepository(session)

    async def post_transaction(self, transaction: Transaction) -> List[LedgerEntry]:
        """
        Create balanced ledger entries for a confirmed transaction.
        Raises BusinessRuleError if the transaction state is invalid.
        Must be called within a DB transaction boundary.
        """
        if transaction.status != TransactionStatus.CONFIRMED:
            raise BusinessRuleError("Only CONFIRMED transactions can be posted to ledger")

        tx_type = transaction.transaction_type
        amount = transaction.amount
        currency = transaction.currency
        posted_at = datetime.now(timezone.utc)

        entries: List[LedgerEntry] = []

        if tx_type == TransactionType.INCOME:
            if not transaction.target_account_id:
                raise BusinessRuleError("INCOME transaction requires a target account")

            offset_account = await self._get_or_create_system_offset_account(
                tenant_id=transaction.tenant_id,
                currency=currency,
                kind="INCOME",
            )

            entries = [
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=transaction.target_account_id,
                    entry_type=EntryType.DEBIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description=f"Income: {transaction.description or ''}",
                ),
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=offset_account.id,
                    entry_type=EntryType.CREDIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description="Income offset (recognized revenue)",
                ),
            ]

            await self._adjust_account_balance(transaction.target_account_id, amount)
            await self._adjust_account_balance(offset_account.id, -amount)

        elif tx_type == TransactionType.EXPENSE:
            if not transaction.source_account_id:
                raise BusinessRuleError("EXPENSE transaction requires a source account")

            offset_account = await self._get_or_create_system_offset_account(
                tenant_id=transaction.tenant_id,
                currency=currency,
                kind="EXPENSE",
            )

            entries = [
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=offset_account.id,
                    entry_type=EntryType.DEBIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description="Expense offset (recognized cost)",
                ),
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=transaction.source_account_id,
                    entry_type=EntryType.CREDIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description=f"Expense: {transaction.description or ''}",
                ),
            ]

            await self._adjust_account_balance(offset_account.id, amount)
            await self._adjust_account_balance(transaction.source_account_id, -amount)

        elif tx_type == TransactionType.TRANSFER:
            if not transaction.source_account_id or not transaction.target_account_id:
                raise BusinessRuleError("TRANSFER transaction requires both source and target accounts")
            if transaction.source_account_id == transaction.target_account_id:
                raise BusinessRuleError("TRANSFER source and target accounts must be different")

            entries = [
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=transaction.target_account_id,
                    entry_type=EntryType.DEBIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description=f"Transfer in: {transaction.description or ''}",
                ),
                LedgerEntry(
                    transaction_id=transaction.id,
                    account_id=transaction.source_account_id,
                    entry_type=EntryType.CREDIT,
                    amount=amount,
                    currency=currency,
                    posted_at=posted_at,
                    description=f"Transfer out: {transaction.description or ''}",
                ),
            ]

            await self._adjust_account_balance(transaction.target_account_id, amount)
            await self._adjust_account_balance(transaction.source_account_id, -amount)

        else:
            raise BusinessRuleError(f"Unsupported transaction type: {tx_type}")

        saved_entries = await self.ledger_repo.create_many(entries)

        is_balanced = await self.ledger_repo.verify_transaction_balance(transaction.id)
        if not is_balanced:
            raise BusinessRuleError(
                f"CRITICAL: Ledger integrity violation — transaction {transaction.id} is unbalanced. Rolling back."
            )

        return saved_entries

    async def post_reversal(
        self,
        original_tx: Transaction,
        reversal_tx: Transaction,
    ) -> List[LedgerEntry]:
        """
        Post reversed/opposite ledger entries for a reversal transaction.
        Account balances are adjusted to undo the original posting.
        """
        if reversal_tx.status != TransactionStatus.CONFIRMED:
            raise BusinessRuleError("Reversal transaction must be CONFIRMED")

        return await self.post_transaction(reversal_tx)

    async def verify_account_integrity(self, account_id: uuid.UUID) -> bool:
        """
        Check that the account's current_balance matches sum of ledger entries.
        """
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise BusinessRuleError("Account not found")

        ledger_balance = await self.ledger_repo.get_account_balance(account_id)
        opening = account.opening_balance or Decimal("0")
        expected_balance = opening + ledger_balance
        return account.current_balance == expected_balance

    async def list_by_account(
        self,
        account_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[LedgerEntry], int]:
        """Return paginated ledger entries for a given account."""
        from sqlalchemy import func

        count_result = await self.session.execute(
            select(func.count(LedgerEntry.id)).where(
                LedgerEntry.account_id == account_id
            )
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.account_id == account_id)
            .order_by(LedgerEntry.posted_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_account_balance_summary(self, account_id: uuid.UUID) -> dict:
        """Return ledger balance and integrity status for an account."""
        ledger_balance = await self.ledger_repo.get_account_balance(account_id)
        is_balanced = await self.verify_account_integrity(account_id)
        return {
            "account_id": account_id,
            "ledger_balance": ledger_balance,
            "is_balanced": is_balanced,
        }

    async def _adjust_account_balance(self, account_id: uuid.UUID, delta: Decimal) -> None:
        """Internal: adjust account current_balance by delta."""
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise BusinessRuleError(f"Account {account_id} not found during ledger posting")

        new_balance = (account.current_balance or Decimal("0")) + delta
        await self.account_repo.update_balance(account_id, new_balance)

    async def _get_or_create_system_offset_account(
        self,
        tenant_id: uuid.UUID,
        currency: str,
        kind: str,
    ) -> Account:
        """
        Create hidden system accounts for ledger offset rows.
        This avoids NULL account_id in ledger_entries.
        """
        if kind not in ("INCOME", "EXPENSE"):
            raise BusinessRuleError(f"Invalid system offset kind: {kind}")

        account_name = f"__SYS_{kind}_OFFSET__ {currency}"

        result = await self.session.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.name == account_name,
                Account.currency == currency,
                Account.is_deleted == False,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        account = Account(
            tenant_id=tenant_id,
            group_id=None,
            name=account_name,
            account_type=AccountType.OTHER,
            currency=currency,
            opening_balance=Decimal("0"),
            current_balance=Decimal("0"),
            institution_name=None,
            iban=None,
            account_number=None,
            description=f"System-managed {kind.lower()} offset account",
            is_active=False,
            include_in_total=False,
        )
        self.session.add(account)
        await self.session.flush()
        await self.session.refresh(account)
        return account
