"""InstitutionService — financial institution and rule management."""
import uuid
import logging
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.institution import (
    InstitutionRepository, CommissionRuleRepository, TaxRuleRepository
)
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class InstitutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InstitutionRepository(db)
        self.commission_repo = CommissionRuleRepository(db)
        self.tax_repo = TaxRuleRepository(db)
        self.audit = AuditService(db)

    async def _attach_groups(self, inst) -> None:
        inst.group_ids = await self.repo.get_group_ids(inst.id)

    async def _attach_groups_bulk(self, institutions: list) -> None:
        if not institutions:
            return
        ids = [i.id for i in institutions]
        group_map = await self.repo.get_group_ids_bulk(ids)
        for inst in institutions:
            inst.group_ids = group_map.get(inst.id, [])

    # ------------------------------------------------------------------ #
    # Institutions
    # ------------------------------------------------------------------ #

    async def create(self, tenant_id: uuid.UUID, actor_id: uuid.UUID, data: dict):
        group_ids = data.pop("group_ids", []) or []
        obj = await self.repo.create(tenant_id, data)
        await self.repo.sync_group_links(obj.id, [uuid.UUID(str(g)) for g in group_ids])
        await self.audit.log(
            actor_id=actor_id, action="institution.create",
            module="institutions", record_id=obj.id,
            new_state={"name": obj.name, "type": obj.institution_type},
        )
        await self.db.commit()
        await self.db.refresh(obj)
        await self._attach_groups(obj)

        # Always auto-create investment account + portfolio for every institution
        await self._auto_create_investment_account_and_portfolio(tenant_id, obj)

        return obj

    async def _auto_create_investment_account_and_portfolio(
        self, tenant_id: uuid.UUID, institution
    ):
        """Create an INVESTMENT account and a Portfolio for ANY institution type."""
        from app.models.account import Account, AccountType
        from app.models.investment import Portfolio

        account_name = f"{institution.name} Yatırım Hesabı"

        # Skip if already exists
        existing = (await self.db.execute(
            select(Account).where(
                Account.tenant_id == tenant_id,
                Account.name == account_name,
                Account.is_deleted == False,
            )
        )).scalar_one_or_none()

        if existing:
            logger.info(f"Investment account '{account_name}' already exists — skipping.")
            return

        # Use the institution's first group (if any) for both account and portfolio
        primary_group_id = None
        inst_group_ids = getattr(institution, "group_ids", [])
        if inst_group_ids:
            primary_group_id = inst_group_ids[0]

        # Create investment account
        account = Account(
            tenant_id=tenant_id,
            name=account_name,
            account_type=AccountType.INVESTMENT,
            currency="TRY",
            opening_balance=Decimal("0"),
            current_balance=Decimal("0"),
            institution_id=institution.id,
            institution_name=institution.name,
            group_id=primary_group_id,
            is_active=True,
            include_in_total=True,
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        logger.info(f"Created investment account: '{account_name}' (id={account.id})")

        # Create linked portfolio
        portfolio = Portfolio(
            tenant_id=tenant_id,
            institution_id=institution.id,
            cash_account_id=account.id,
            name=f"{institution.name} Portföyü",
            currency="TRY",
            group_id=primary_group_id,
            is_active=True,
        )
        self.db.add(portfolio)
        await self.db.flush()
        logger.info(f"Created portfolio: '{institution.name} Portföyü'")

        await self.db.commit()

    # ------------------------------------------------------------------ #

    async def update(
        self, institution_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        group_ids = data.pop("group_ids", None)
        inst = await self._get_or_404(institution_id, tenant_id)
        updated = await self.repo.update(inst, data)
        if group_ids is not None:
            typed_ids = [uuid.UUID(str(g)) for g in group_ids]
            await self.repo.sync_group_links(institution_id, typed_ids)
            # Propagate primary group to linked portfolio and investment account
            primary_group_id = typed_ids[0] if typed_ids else None
            await self._sync_portfolio_and_account_group(
                tenant_id, institution_id, primary_group_id
            )
        await self.db.commit()
        await self.db.refresh(updated)
        await self._attach_groups(updated)
        return updated

    async def _sync_portfolio_and_account_group(
        self, tenant_id: uuid.UUID, institution_id: uuid.UUID,
        group_id: Optional[uuid.UUID]
    ) -> None:
        """Update group_id on the institution's linked portfolio and investment account."""
        from app.models.investment import Portfolio
        from app.models.account import Account
        from sqlalchemy import update as sa_update

        await self.db.execute(
            sa_update(Portfolio)
            .where(Portfolio.institution_id == institution_id, Portfolio.tenant_id == tenant_id)
            .values(group_id=group_id)
        )
        await self.db.execute(
            sa_update(Account)
            .where(Account.institution_id == institution_id, Account.tenant_id == tenant_id,
                   Account.is_deleted == False)
            .values(group_id=group_id)
        )

    async def delete(
        self, institution_id: uuid.UUID, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ):
        from app.models.account import Account
        from app.models.investment import Portfolio
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        from app.services.ledger_service import LedgerService
        from sqlalchemy import func, or_
        from datetime import date

        inst = await self._get_or_404(institution_id, tenant_id)

        # Find the linked investment account
        linked_account = (await self.db.execute(
            select(Account).where(
                Account.institution_id == institution_id,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False,
            )
        )).scalar_one_or_none()

        if linked_account:
            balance = linked_account.current_balance or Decimal("0")

            # If there is remaining balance, transfer it back to the original source account
            if balance > 0:
                # Find the most recent transaction that brought money INTO this account
                # (any transaction where target = investment account AND source exists = came from somewhere)
                incoming = (await self.db.execute(
                    select(Transaction)
                    .where(
                        Transaction.target_account_id == linked_account.id,
                        Transaction.source_account_id.is_not(None),
                        Transaction.is_deleted == False,
                    )
                    .order_by(Transaction.transaction_date.desc())
                    .limit(1)
                )).scalar_one_or_none()

                if incoming and incoming.source_account_id:
                    # Verify the source account still exists
                    source_account = (await self.db.execute(
                        select(Account).where(
                            Account.id == incoming.source_account_id,
                            Account.is_deleted == False,
                        )
                    )).scalar_one_or_none()

                    if source_account:
                        # Transfer the balance back
                        return_tx = Transaction(
                            tenant_id=tenant_id,
                            transaction_type=TransactionType.TRANSFER,
                            status=TransactionStatus.CONFIRMED,
                            amount=balance,
                            currency=linked_account.currency,
                            source_account_id=linked_account.id,
                            target_account_id=source_account.id,
                            transaction_date=date.today(),
                            description=f"Hesap Kapatma - {inst.name} bakiye iadesi",
                        )
                        self.db.add(return_tx)
                        await self.db.flush()
                        ledger = LedgerService(self.db)
                        await ledger.post_transaction(return_tx)
                        logger.info(
                            f"Transferred {balance} {linked_account.currency} "
                            f"from '{linked_account.name}' back to '{source_account.name}'."
                        )
                    else:
                        logger.warning(
                            f"Source account {incoming.source_account_id} not found; "
                            f"balance {balance} will be dropped on account deletion."
                        )

            # Soft-delete all linked portfolios (and their positions via cascade or is_deleted)
            portfolios = (await self.db.execute(
                select(Portfolio).where(
                    Portfolio.institution_id == institution_id,
                    Portfolio.tenant_id == tenant_id,
                    Portfolio.is_deleted == False,
                )
            )).scalars().all()
            for p in portfolios:
                p.is_deleted = True
                logger.info(f"Soft-deleted portfolio '{p.name}'.")

            # Soft-delete the account itself
            linked_account.is_deleted = True
            await self.db.flush()
            logger.info(f"Soft-deleted account '{linked_account.name}'.")

        # Soft-delete the institution
        await self.repo.soft_delete(inst)
        await self.audit.log(
            actor_id=actor_id, action="institution.delete",
            module="institutions", record_id=institution_id,
        )
        await self.db.commit()

    async def get(self, institution_id: uuid.UUID, tenant_id: uuid.UUID):
        inst = await self._get_or_404(institution_id, tenant_id)
        await self._attach_groups(inst)
        return inst

    async def list(
        self, tenant_id: uuid.UUID,
        institution_type: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0, limit: int = 100,
        group_ids: Optional[list] = None,
    ):
        institutions = await self.repo.list_by_tenant(
            tenant_id, institution_type=institution_type,
            active_only=active_only, skip=skip, limit=limit,
            group_ids=group_ids,
        )
        await self._attach_groups_bulk(institutions)
        return institutions

    # ------------------------------------------------------------------ #
    # Commission Rules
    # ------------------------------------------------------------------ #

    async def add_commission_rule(
        self, institution_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        await self._get_or_404(institution_id, tenant_id)
        rule = await self.commission_repo.create(institution_id, data)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def list_commission_rules(
        self, institution_id: uuid.UUID, tenant_id: uuid.UUID
    ):
        await self._get_or_404(institution_id, tenant_id)
        return await self.commission_repo.list_by_institution(institution_id)

    async def delete_commission_rule(
        self, institution_id: uuid.UUID, rule_id: uuid.UUID, tenant_id: uuid.UUID
    ):
        await self._get_or_404(institution_id, tenant_id)
        rules = await self.commission_repo.list_by_institution(institution_id)
        rule = next((r for r in rules if r.id == rule_id), None)
        if not rule:
            raise HTTPException(status_code=404, detail="Commission rule not found.")
        await self.commission_repo.delete(rule)
        await self.db.commit()

    # ------------------------------------------------------------------ #
    # Tax Rules
    # ------------------------------------------------------------------ #

    async def add_tax_rule(
        self, institution_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        await self._get_or_404(institution_id, tenant_id)
        rule = await self.tax_repo.create(institution_id, data)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def list_tax_rules(self, institution_id: uuid.UUID, tenant_id: uuid.UUID):
        await self._get_or_404(institution_id, tenant_id)
        return await self.tax_repo.list_by_institution(institution_id)

    async def delete_tax_rule(
        self, institution_id: uuid.UUID, rule_id: uuid.UUID, tenant_id: uuid.UUID
    ):
        await self._get_or_404(institution_id, tenant_id)
        rules = await self.tax_repo.list_by_institution(institution_id)
        rule = next((r for r in rules if r.id == rule_id), None)
        if not rule:
            raise HTTPException(status_code=404, detail="Tax rule not found.")
        await self.tax_repo.delete(rule)
        await self.db.commit()

    # ------------------------------------------------------------------ #

    async def _get_or_404(self, institution_id: uuid.UUID, tenant_id: uuid.UUID):
        inst = await self.repo.get_by_id(institution_id, tenant_id)
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found.")
        return inst
