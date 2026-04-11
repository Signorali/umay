"""
Transaction Service — orchestrates transaction creation and lifecycle.

Critical rules:
1. Every CONFIRMED transaction MUST produce ledger entries (via LedgerService)
2. No partial writes — use DB transaction boundaries
3. Cancellation and reversal do NOT delete ledger entries
4. Reversal creates a counter-transaction, not a delete
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionType, TransactionStatus, TransactionTag
from app.repositories.transaction import TransactionRepository
from app.repositories.account import AccountRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService
from app.services.period_lock_service import PeriodLockService
from app.core.exceptions import NotFoundError, BusinessRuleError


class TransactionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TransactionRepository(session)
        self.account_repo = AccountRepository(session)
        self.ledger = LedgerService(session)
        self.audit = AuditService(session)
        self.period_lock = PeriodLockService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        group_id: Optional[uuid.UUID],
        data: TransactionCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
        force: bool = False,
    ) -> Transaction:
        """Create a transaction. If status is CONFIRMED, post to ledger immediately."""
        # Period lock check
        await self.period_lock.assert_period_open(data.transaction_date, force=force)

        await self._validate_accounts(
            data.transaction_type, data.source_account_id,
            data.target_account_id, tenant_id
        )

        tx = Transaction(
            tenant_id=tenant_id,
            group_id=group_id,
            transaction_type=data.transaction_type,
            status=data.status,
            amount=data.amount,
            currency=data.currency,
            source_account_id=data.source_account_id,
            target_account_id=data.target_account_id,
            category_id=data.category_id,
            transaction_date=data.transaction_date,
            value_date=data.value_date,
            description=data.description,
            notes=data.notes,
            reference_number=data.reference_number,
        )
        tx = await self.repo.create(tx)

        # Add tags
        if data.tags:
            for tag in data.tags:
                t = TransactionTag(transaction_id=tx.id, tag=tag)
                self.session.add(t)
            await self.session.flush()

        # Post to ledger if CONFIRMED
        if tx.status == TransactionStatus.CONFIRMED:
            await self.ledger.post_transaction(tx)

        await self.audit.log(
            action="CREATE",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx.id),
            after={
                "type": tx.transaction_type,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "status": tx.status,
            },
        )
        return tx

    async def update(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: "TransactionUpdate",
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Transaction:
        """Update a DRAFT transaction's non-financial fields.
        Only DRAFT transactions can be edited.
        Financial fields (amount, type, accounts) cannot be changed after creation.
        """
        tx = await self._get_or_raise(tx_id, tenant_id)
        if tx.status != TransactionStatus.DRAFT:
            raise BusinessRuleError(
                "Only DRAFT transactions can be edited. "
                "Confirmed transactions require reversal."
            )

        before_snapshot = {
            "description": tx.description,
            "notes": tx.notes,
            "reference_number": tx.reference_number,
            "category_id": str(tx.category_id) if tx.category_id else None,
            "value_date": str(tx.value_date) if tx.value_date else None,
        }

        update_fields = data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(tx, field, value)

        await self.session.flush()
        await self.session.refresh(tx)

        await self.audit.log(
            action="UPDATE",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx_id),
            before=before_snapshot,
            after=update_fields,
        )
        return tx

    async def confirm(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Transaction:
        """Confirm a DRAFT transaction and post its ledger entries."""
        tx = await self._get_or_raise(tx_id, tenant_id)
        if tx.status != TransactionStatus.DRAFT:
            raise BusinessRuleError(f"Only DRAFT transactions can be confirmed. Current: {tx.status}")

        tx = await self.repo.update(tx, status=TransactionStatus.CONFIRMED)
        await self.ledger.post_transaction(tx)

        await self.audit.log(
            action="CONFIRM",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx_id),
            before={"status": "DRAFT"},
            after={"status": "CONFIRMED"},
        )
        return tx

    async def cancel(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Transaction:
        """Cancel a DRAFT transaction. Confirmed transactions must be reversed."""
        tx = await self._get_or_raise(tx_id, tenant_id)
        if tx.status != TransactionStatus.DRAFT:
            raise BusinessRuleError(
                "Only DRAFT transactions can be cancelled. "
                "Use reversal for CONFIRMED transactions."
            )

        tx = await self.repo.update(tx, status=TransactionStatus.CANCELLED)
        await self.audit.log(
            action="CANCEL",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx_id),
        )
        return tx

    async def reverse(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        description: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Transaction:
        """
        Reverse a CONFIRMED transaction.
        Creates a counter-transaction with swapped accounts and posts it to ledger.
        Never deletes original ledger entries.
        """
        original = await self._get_or_raise(tx_id, tenant_id)
        if original.status != TransactionStatus.CONFIRMED:
            raise BusinessRuleError("Only CONFIRMED transactions can be reversed")
        if original.reversed_by_id:
            raise BusinessRuleError("This transaction has already been reversed")

        # Build the reversal transaction (swap source/target for transfers)
        reversal_source = original.target_account_id
        reversal_target = original.source_account_id

        if original.transaction_type == TransactionType.INCOME:
            # Reverse income: money goes OUT of target account
            reversal_source = original.target_account_id
            reversal_target = None
        elif original.transaction_type == TransactionType.EXPENSE:
            # Reverse expense: money comes BACK to source account
            reversal_source = None
            reversal_target = original.source_account_id

        reversal = Transaction(
            tenant_id=original.tenant_id,
            group_id=original.group_id,
            transaction_type=original.transaction_type,
            status=TransactionStatus.CONFIRMED,
            amount=original.amount,
            currency=original.currency,
            source_account_id=reversal_source,
            target_account_id=reversal_target,
            category_id=original.category_id,
            transaction_date=datetime.now(timezone.utc).date(),
            description=description or f"Reversal of transaction {original.id}",
            reversal_of_id=original.id,
        )
        reversal = await self.repo.create(reversal)

        # Mark original as reversed
        await self.repo.update(original, status=TransactionStatus.REVERSED, reversed_by_id=reversal.id)

        # Post reversal ledger entries
        await self.ledger.post_transaction(reversal)

        await self.audit.log(
            action="REVERSE",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx_id),
            after={"reversal_transaction_id": str(reversal.id)},
        )
        return reversal

    async def get_by_id(self, tx_id: uuid.UUID, tenant_id: uuid.UUID) -> Transaction:
        return await self._get_or_raise(tx_id, tenant_id)

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status=None,
        transaction_type=None,
        date_from=None,
        date_to=None,
        account_id=None,
        group_ids: Optional[List[uuid.UUID]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Transaction], int]:
        return await self.repo.get_by_tenant(
            tenant_id,
            status=status,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            account_id=account_id,
            group_ids=group_ids,
            offset=offset,
            limit=limit,
        )

    async def delete(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        """Delete a transaction. CONFIRMED transactions have their balance impact reversed first."""
        tx = await self._get_or_raise(tx_id, tenant_id)

        if tx.status == TransactionStatus.CONFIRMED:
            # Reverse balance impact before deleting
            amount = tx.amount
            if tx.transaction_type == TransactionType.INCOME and tx.target_account_id:
                await self.ledger._adjust_account_balance(tx.target_account_id, -amount)
            elif tx.transaction_type == TransactionType.EXPENSE and tx.source_account_id:
                await self.ledger._adjust_account_balance(tx.source_account_id, amount)
            elif tx.transaction_type == TransactionType.TRANSFER:
                if tx.target_account_id:
                    await self.ledger._adjust_account_balance(tx.target_account_id, -amount)
                if tx.source_account_id:
                    await self.ledger._adjust_account_balance(tx.source_account_id, amount)

        await self.repo.soft_delete(tx)

        # Reset any linked planned payment back to PENDING
        if tx.status == TransactionStatus.CONFIRMED:
            from sqlalchemy import select
            from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus
            result = await self.session.execute(
                select(PlannedPayment).where(
                    PlannedPayment.linked_transaction_id == tx_id,
                    PlannedPayment.is_deleted == False,
                )
            )
            linked_pp = result.scalar_one_or_none()
            if linked_pp:
                linked_pp.status = PlannedPaymentStatus.PENDING
                linked_pp.paid_amount = 0
                linked_pp.linked_transaction_id = None
                await self.session.flush()

            # Reset any linked loan installment back to PENDING and update loan totals
            from app.models.loan import Loan, LoanInstallment, InstallmentStatus, LoanStatus
            result = await self.session.execute(
                select(LoanInstallment).where(
                    LoanInstallment.linked_transaction_id == tx_id,
                    LoanInstallment.is_deleted == False,
                )
            )
            linked_inst = result.scalar_one_or_none()
            if linked_inst:
                linked_inst.status = InstallmentStatus.PENDING
                linked_inst.paid_amount = Decimal("0")
                linked_inst.paid_date = None
                linked_inst.linked_transaction_id = None
                
                # Update loan totals
                loan = await self.session.get(Loan, linked_inst.loan_id)
                if loan:
                    loan.total_paid = (loan.total_paid or Decimal("0")) - tx.amount
                    loan.remaining_balance = (loan.remaining_balance or Decimal("0")) + tx.amount
                    if loan.status == LoanStatus.PAID_OFF:
                        loan.status = LoanStatus.ACTIVE
                
                await self.session.flush()


        # Revert any sold/disposed asset linked to this transaction
        if tx.status == TransactionStatus.CONFIRMED:
            from sqlalchemy import select as sa_select
            from app.models.asset import Asset, AssetStatus
            asset_result = await self.session.execute(
                sa_select(Asset).where(
                    Asset.sale_transaction_id == tx_id,
                    Asset.is_deleted == False,
                )
            )
            linked_asset = asset_result.scalar_one_or_none()
            if linked_asset:
                linked_asset.status = AssetStatus.OWNED
                linked_asset.sale_date = None
                linked_asset.sale_value = None
                linked_asset.sale_notes = None
                linked_asset.sale_transaction_id = None
                await self.session.flush()

        await self.audit.log(
            action="DELETE",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tx_id),
            before={"status": tx.status, "amount": str(tx.amount), "type": tx.transaction_type},
        )


    async def _get_or_raise(self, tx_id: uuid.UUID, tenant_id: uuid.UUID) -> Transaction:
        tx = await self.repo.get_by_id_and_tenant(tx_id, tenant_id)
        if not tx:
            raise NotFoundError("Transaction")
        return tx

    async def _validate_accounts(
        self,
        tx_type: TransactionType,
        source_id: Optional[uuid.UUID],
        target_id: Optional[uuid.UUID],
        tenant_id: uuid.UUID,
    ) -> None:
        if tx_type == TransactionType.INCOME and not target_id:
            raise BusinessRuleError("INCOME transaction requires a target account")
        if tx_type == TransactionType.EXPENSE and not source_id:
            raise BusinessRuleError("EXPENSE transaction requires a source account")
        if tx_type == TransactionType.TRANSFER:
            if not source_id or not target_id:
                raise BusinessRuleError("TRANSFER requires both source and target accounts")
            if source_id == target_id:
                raise BusinessRuleError("TRANSFER source and target must be different accounts")

        # Verify accounts belong to tenant
        for acct_id in [source_id, target_id]:
            if acct_id:
                account = await self.account_repo.get_by_id_and_tenant(acct_id, tenant_id)
                if not account:
                    raise NotFoundError(f"Account {acct_id}")
                if not account.is_active:
                    raise BusinessRuleError(f"Account '{account.name}' is inactive")

    async def _populate_transaction_names(self, transactions: List[Transaction]) -> List[dict]:
        """Convert Transaction models to dicts with account/group names populated."""
        from sqlalchemy import select
        from app.models.account import Account
        from app.models.group import Group

        result_list = []

        # Collect all account IDs we need to fetch
        account_ids = set()
        for tx in transactions:
            if tx.source_account_id:
                account_ids.add(tx.source_account_id)
            if tx.target_account_id:
                account_ids.add(tx.target_account_id)

        # Fetch all accounts in one query
        accounts_map = {}
        if account_ids:
            accounts_result = await self.session.execute(
                select(Account).where(Account.id.in_(account_ids))
            )
            for account in accounts_result.scalars().all():
                accounts_map[account.id] = account

        # Convert transactions to dicts with names
        for tx in transactions:
            tx_dict = {
                'id': tx.id,
                'tenant_id': tx.tenant_id,
                'group_id': tx.group_id,
                'transaction_type': tx.transaction_type,
                'status': tx.status,
                'amount': tx.amount,
                'currency': tx.currency,
                'source_account_id': tx.source_account_id,
                'target_account_id': tx.target_account_id,
                'source_account_name': None,
                'target_account_name': None,
                'source_group_name': None,
                'target_group_name': None,
                'category_id': tx.category_id,
                'transaction_date': tx.transaction_date,
                'value_date': tx.value_date,
                'description': tx.description,
                'notes': tx.notes,
                'reference_number': tx.reference_number,
                'reversed_by_id': tx.reversed_by_id,
                'reversal_of_id': tx.reversal_of_id,
                'created_at': tx.created_at,
            }

            # Add account names and group names
            if tx.source_account_id and tx.source_account_id in accounts_map:
                source_acc = accounts_map[tx.source_account_id]
                tx_dict['source_account_name'] = source_acc.name
                tx_dict['source_group_name'] = source_acc.name  # Will be replaced with actual group name

            if tx.target_account_id and tx.target_account_id in accounts_map:
                target_acc = accounts_map[tx.target_account_id]
                tx_dict['target_account_name'] = target_acc.name
                tx_dict['target_group_name'] = target_acc.name  # Will be replaced with actual group name

            # Fetch group names if we have source/target accounts
            if tx.source_account_id and tx.source_account_id in accounts_map:
                source_acc = accounts_map[tx.source_account_id]
                group_result = await self.session.execute(
                    select(Group).where(Group.id == source_acc.group_id)
                )
                group = group_result.scalar_one_or_none()
                if group:
                    tx_dict['source_group_name'] = group.name

            if tx.target_account_id and tx.target_account_id in accounts_map:
                target_acc = accounts_map[tx.target_account_id]
                group_result = await self.session.execute(
                    select(Group).where(Group.id == target_acc.group_id)
                )
                group = group_result.scalar_one_or_none()
                if group:
                    tx_dict['target_group_name'] = group.name

            result_list.append(tx_dict)

        return result_list
