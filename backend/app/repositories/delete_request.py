import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delete_request import DeleteRequest


class DeleteRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, request_id: uuid.UUID) -> Optional[DeleteRequest]:
        result = await self.session.get(DeleteRequest, request_id)
        if result and not result.is_deleted:
            return result
        return None

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeleteRequest], int]:
        query = (
            select(DeleteRequest)
            .where(DeleteRequest.tenant_id == tenant_id, DeleteRequest.is_deleted == False)
        )
        if status:
            query = query.where(DeleteRequest.status == status)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_q)).scalar_one()

        query = query.order_by(DeleteRequest.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), total

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeleteRequest], int]:
        query = (
            select(DeleteRequest)
            .where(
                DeleteRequest.requested_by_user_id == user_id,
                DeleteRequest.tenant_id == tenant_id,
                DeleteRequest.is_deleted == False,
            )
            .order_by(DeleteRequest.created_at.desc())
        )
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_q)).scalar_one()
        rows = (await self.session.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get_pending_for_target(
        self, target_table: str, target_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[DeleteRequest]:
        result = await self.session.execute(
            select(DeleteRequest).where(
                DeleteRequest.target_table == target_table,
                DeleteRequest.target_id == target_id,
                DeleteRequest.tenant_id == tenant_id,
                DeleteRequest.status == "pending",
                DeleteRequest.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, obj: DeleteRequest) -> DeleteRequest:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: DeleteRequest, **kwargs) -> DeleteRequest:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
