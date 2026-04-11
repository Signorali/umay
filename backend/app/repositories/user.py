import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str, tenant_id: uuid.UUID) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
                User.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tenant(self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20):
        return await self.list_all(
            filters=[User.tenant_id == tenant_id],
            offset=offset,
            limit=limit,
        )

    async def email_exists(self, email: str, tenant_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(User.id).where(User.email == email, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none() is not None

    async def record_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        user.failed_login_count = 0
        user.locked_until = None
        await self.session.flush()

    async def increment_failed_login(self, user: User, lock_until: Optional[datetime] = None) -> None:
        user.failed_login_count += 1
        if lock_until:
            user.locked_until = lock_until
        await self.session.flush()
