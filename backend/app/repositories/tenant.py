from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tenant, session)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        result = await self.session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        result = await self.session.execute(
            select(Tenant.id).where(Tenant.slug == slug)
        )
        return result.scalar_one_or_none() is not None
