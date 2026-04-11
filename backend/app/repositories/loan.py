"""Loan and LoanInstallment repositories."""
import uuid
from typing import List, Optional, Tuple, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan, LoanInstallment, LoanStatus, InstallmentStatus
from app.repositories.base import BaseRepository


class LoanRepository(BaseRepository[Loan]):
    def __init__(self, session: AsyncSession):
        super().__init__(Loan, session)

    async def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[LoanStatus] = None,
        offset: int = 0,
        limit: int = 50,
        group_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[List[Loan], int]:
        filters = [Loan.tenant_id == tenant_id]
        if status:
            filters.append(Loan.status == status)
        if group_ids:
            filters.append(Loan.group_id.in_(group_ids))
        return await self.list_all(filters=filters, offset=offset, limit=limit)

    async def get_by_id_and_tenant(
        self, loan_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Loan]:
        result = await self.session.execute(
            select(Loan).where(
                Loan.id == loan_id,
                Loan.tenant_id == tenant_id,
                Loan.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()


class LoanInstallmentRepository(BaseRepository[LoanInstallment]):
    def __init__(self, session: AsyncSession):
        super().__init__(LoanInstallment, session)

    async def get_by_loan(self, loan_id: uuid.UUID) -> List[LoanInstallment]:
        result = await self.session.execute(
            select(LoanInstallment).where(
                LoanInstallment.loan_id == loan_id,
                LoanInstallment.is_deleted == False,
            ).order_by(LoanInstallment.installment_number)
        )
        return list(result.scalars().all())

    async def get_pending_by_loan(self, loan_id: uuid.UUID) -> List[LoanInstallment]:
        result = await self.session.execute(
            select(LoanInstallment).where(
                LoanInstallment.loan_id == loan_id,
                LoanInstallment.status == InstallmentStatus.PENDING,
                LoanInstallment.is_deleted == False,
            ).order_by(LoanInstallment.installment_number)
        )
        return list(result.scalars().all())
