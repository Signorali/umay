"""Account service."""
import uuid
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.repositories.account import AccountRepository
from app.schemas.account import AccountCreate, AccountUpdate
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleError


class AccountService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AccountRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: AccountCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Account:
        if await self.repo.name_exists(data.name, tenant_id):
            raise ConflictError(f"Account '{data.name}' already exists in this tenant")

        account = Account(
            tenant_id=tenant_id,
            group_id=data.group_id,
            name=data.name,
            account_type=data.account_type,
            currency=data.currency,
            opening_balance=data.opening_balance,
            current_balance=data.opening_balance,  # Start from opening balance
            institution_name=data.institution_name,
            iban=data.iban,
            account_number=data.account_number,
            description=data.description,
            include_in_total=data.include_in_total,
            allow_negative_balance=data.allow_negative_balance,
        )
        account = await self.repo.create(account)
        await self.audit.log(
            action="CREATE",
            module="accounts",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(account.id),
            after={"name": account.name, "type": account.account_type, "currency": account.currency},
        )
        return account

    async def get_by_id(self, account_id: uuid.UUID, tenant_id: uuid.UUID) -> Account:
        account = await self.repo.get_by_id_and_tenant(account_id, tenant_id)
        if not account:
            raise NotFoundError("Account")
        return account

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50,
        include_system: bool = False, group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[Account], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit,
                                             include_system=include_system, group_ids=group_ids)

    async def update(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: AccountUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Account:
        account = await self.get_by_id(account_id, tenant_id)
        before = {"name": account.name, "is_active": account.is_active}

        if data.name and data.name != account.name:
            if await self.repo.name_exists(data.name, tenant_id):
                raise ConflictError(f"Account '{data.name}' already exists in this tenant")

        update_fields = data.model_dump(exclude_none=True)
        account = await self.repo.update(account, **update_fields)
        await self.audit.log(
            action="UPDATE",
            module="accounts",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(account_id),
            before=before,
            after=update_fields,
        )
        return account

    async def delete(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        account = await self.get_by_id(account_id, tenant_id)
        if await self.repo.has_transactions(account_id):
            raise BusinessRuleError(
                "Cannot delete an account that has transactions linked to it. "
                "Delete the transactions or transfer them first."
            )
        await self.repo.soft_delete(account)
        await self.audit.log(
            action="DELETE",
            module="accounts",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(account_id),
        )
