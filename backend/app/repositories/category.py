"""Category repository."""
import uuid
from typing import List, Optional, Tuple, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session: AsyncSession):
        super().__init__(Category, session)

    async def get_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 100,
        group_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[List[Category], int]:
        filters = [Category.tenant_id == tenant_id]
        if group_ids:
            from sqlalchemy import or_
            # Show system categories (no group) + user's group categories
            filters.append(or_(Category.group_id == None, Category.group_id.in_(group_ids)))
        return await self.list_all(
            filters=filters,
            offset=offset,
            limit=limit,
        )

    async def get_by_type(
        self, category_type: CategoryType, tenant_id: uuid.UUID
    ) -> List[Category]:
        result = await self.session.execute(
            select(Category).where(
                Category.category_type == category_type,
                Category.tenant_id == tenant_id,
                Category.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def get_by_id_and_tenant(
        self, category_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Category]:
        result = await self.session.execute(
            select(Category).where(
                Category.id == category_id,
                Category.tenant_id == tenant_id,
                Category.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: uuid.UUID) -> List[Category]:
        result = await self.session.execute(
            select(Category).where(
                Category.parent_id == parent_id,
                Category.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def name_exists(
        self, name: str, tenant_id: uuid.UUID, parent_id: Optional[uuid.UUID] = None
    ) -> bool:
        query = select(Category.id).where(
            Category.name == name,
            Category.tenant_id == tenant_id,
            Category.is_deleted == False,
        )
        if parent_id:
            query = query.where(Category.parent_id == parent_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
