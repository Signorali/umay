import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.transaction import Transaction
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate, PasswordChange
from app.services.audit_service import AuditService
from app.core.security import hash_password, verify_password
from app.core.exceptions import ConflictError, NotFoundError, BusinessRuleError


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: UserCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> User:
        if await self.repo.email_exists(data.email, tenant_id):
            raise ConflictError(f"Email '{data.email}' is already registered in this tenant")

        user = User(
            tenant_id=tenant_id,
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role_id=data.role_id,
            is_tenant_admin=data.is_tenant_admin,
            locale=data.locale,
            timezone=data.timezone,
        )
        user = await self.repo.create(user)

        await self.audit.log(
            action="CREATE",
            module="users",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(user.id),
            after={"email": user.email, "full_name": user.full_name},
        )
        return user

    async def get_by_id(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundError("User")
        return user

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[User], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit)

    async def update(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: UserUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> User:
        user = await self.get_by_id(user_id, tenant_id)
        before = {"full_name": user.full_name, "is_active": user.is_active}

        update_fields = data.model_dump(exclude_none=True)
        user = await self.repo.update(user, **update_fields)

        await self.audit.log(
            action="UPDATE",
            module="users",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(user_id),
            before=before,
            after=update_fields,
        )
        return user

    async def change_password(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: PasswordChange,
    ) -> None:
        user = await self.get_by_id(user_id, tenant_id)
        if not verify_password(data.current_password, user.hashed_password):
            raise BusinessRuleError("Current password is incorrect")
        await self.repo.update(user, hashed_password=hash_password(data.new_password))
        await self.audit.log(
            action="PASSWORD_CHANGE",
            module="users",
            tenant_id=tenant_id,
            actor_id=user_id,
            record_id=str(user_id),
        )

    async def admin_reset_password(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        new_password: str,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> User:
        """Admin sets a new password for a user; forces must_change_password on next login."""
        user = await self.get_by_id(user_id, tenant_id)
        user = await self.repo.update(
            user,
            hashed_password=hash_password(new_password),
            must_change_password=True,
        )
        await self.audit.log(
            action="ADMIN_PASSWORD_RESET",
            module="users",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(user_id),
        )
        return user

    async def deactivate(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> User:
        user = await self.get_by_id(user_id, tenant_id)
        user = await self.repo.update(user, is_active=False)
        await self.audit.log(
            action="DEACTIVATE",
            module="users",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(user_id),
        )
        return user

    async def delete(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        """Hard-delete a user. Only allowed if the user has no transactions."""
        user = await self.get_by_id(user_id, tenant_id)

        # Block deletion if user has any transactions
        tx_count = (await self.session.execute(
            select(func.count()).select_from(Transaction).where(
                Transaction.created_by_user_id == user_id,
                Transaction.tenant_id == tenant_id,
                Transaction.is_deleted == False,
            )
        )).scalar_one()

        if tx_count > 0:
            raise BusinessRuleError(
                f"Bu kullanıcı {tx_count} işlem kaydına sahip olduğu için silinemez. "
                "Önce devre dışı bırakabilirsiniz."
            )

        await self.audit.log(
            action="DELETE",
            module="users",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(user_id),
            before={"email": user.email, "full_name": user.full_name},
        )
        await self.session.delete(user)
