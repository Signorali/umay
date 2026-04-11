import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.user import UserGroup
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    def __init__(self, session: AsyncSession):
        super().__init__(Group, session)

    async def get_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Group], int]:
        return await self.list_all(
            filters=[Group.tenant_id == tenant_id],
            offset=offset,
            limit=limit,
        )

    async def get_by_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Group], int]:
        base_q = (
            select(Group)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(
                UserGroup.user_id == user_id,
                Group.tenant_id == tenant_id,
                Group.is_deleted == False,
                Group.is_active == True,
            )
        )
        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.session.execute(count_q)).scalar_one()
        items = (
            await self.session.execute(base_q.offset(offset).limit(limit))
        ).scalars().all()
        return list(items), total

    async def get_user_group_ids(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[uuid.UUID]:
        result = await self.session.execute(
            select(Group.id)
            .join(UserGroup, UserGroup.group_id == Group.id)
            .where(
                UserGroup.user_id == user_id,
                Group.tenant_id == tenant_id,
                Group.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def name_exists(self, name: str, tenant_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(Group.id).where(
                Group.name == name,
                Group.tenant_id == tenant_id,
                Group.is_deleted == False,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id_and_tenant(
        self, group_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Group]:
        result = await self.session.execute(
            select(Group).where(
                Group.id == group_id,
                Group.tenant_id == tenant_id,
                Group.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def is_user_in_group(self, user_id: uuid.UUID, group_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(UserGroup.group_id).where(
                UserGroup.user_id == user_id,
                UserGroup.group_id == group_id,
            )
        )
        return result.scalar_one_or_none() is not None
