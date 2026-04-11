"""Account repository."""
import uuid
from typing import List, Optional, Tuple, Sequence
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 50,
        include_system: bool = False,
        group_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[List[Account], int]:
        filters = [Account.tenant_id == tenant_id, Account.is_deleted == False]
        if not include_system:
            filters.append(~Account.name.startswith("__SYS_"))
        # NOTE: group_ids filter removed — all tenant accounts are visible to all users.
        # Balance visibility is enforced at the API layer via is_own_group flag.

        return await self.list_all(
            filters=filters,
            offset=offset,
            limit=limit,
        )

    async def get_by_group(
        self, group_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[Account]:
        result = await self.session.execute(
            select(Account).where(
                Account.group_id == group_id,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False,
                ~Account.name.startswith("__SYS_")
            )
        )
        return list(result.scalars().all())

    async def get_by_id_and_tenant(
        self, account_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Account]:
        result = await self.session.execute(
            select(Account).where(
                Account.id == account_id,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def update_balance(
        self, account_id: uuid.UUID, new_balance: Decimal
    ) -> None:
        account = await self.session.get(Account, account_id)
        if account:
            account.current_balance = new_balance
            await self.session.flush()

    async def name_exists(self, name: str, tenant_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(Account.id).where(
                Account.name == name,
                Account.tenant_id == tenant_id,
                Account.is_deleted == False,
            )
        )
        return result.scalar_one_or_none() is not None

    async def has_transactions(self, account_id: uuid.UUID) -> bool:
        from app.models.transaction import Transaction
        from sqlalchemy import or_
        result = await self.session.execute(
            select(Transaction.id).where(
                or_(
                    Transaction.source_account_id == account_id,
                    Transaction.target_account_id == account_id,
                ),
                Transaction.is_deleted == False,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
