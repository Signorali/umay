"""Transaction repository."""
import uuid
from datetime import date
from typing import List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, session: AsyncSession):
        super().__init__(Transaction, session)

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[TransactionStatus] = None,
        transaction_type: Optional[TransactionType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        account_id: Optional[uuid.UUID] = None,
        group_ids: Optional[List[uuid.UUID]] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Transaction], int]:
        filters = [Transaction.tenant_id == tenant_id]

        if status:
            filters.append(Transaction.status == status)
        if transaction_type:
            filters.append(Transaction.transaction_type == transaction_type)
        if date_from:
            filters.append(Transaction.transaction_date >= date_from)
        if date_to:
            filters.append(Transaction.transaction_date <= date_to)
        if account_id:
            filters.append(
                (Transaction.source_account_id == account_id) |
                (Transaction.target_account_id == account_id)
            )
        if group_ids:
            filters.append(Transaction.group_id.in_(group_ids))

        return await self.list_all(filters=filters, offset=offset, limit=limit)

    async def get_by_id_and_tenant(
        self, tx_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Transaction]:
        result = await self.session.execute(
            select(Transaction).where(
                Transaction.id == tx_id,
                Transaction.tenant_id == tenant_id,
                Transaction.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_account(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Transaction], int]:
        return await self.list_all(
            filters=[
                Transaction.tenant_id == tenant_id,
                Transaction.status == TransactionStatus.CONFIRMED,
                (Transaction.source_account_id == account_id) |
                (Transaction.target_account_id == account_id),
            ],
            offset=offset,
            limit=limit,
        )
