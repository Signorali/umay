import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.permission import Permission, RolePermission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_tenant(self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20):
        return await self.list_all(
            filters=[Role.tenant_id == tenant_id],
            offset=offset,
            limit=limit,
        )

    async def name_exists(self, name: str, tenant_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(Role.id).where(
                Role.name == name,
                Role.tenant_id == tenant_id,
                Role.is_deleted == False,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_id_and_tenant(
        self, role_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Role]:
        result = await self.session.execute(
            select(Role).where(
                Role.id == role_id,
                Role.tenant_id == tenant_id,
                Role.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()


class PermissionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.is_deleted == False)
        )
        return list(result.scalars().all())

    async def get_by_id(self, permission_id: uuid.UUID) -> Optional[Permission]:
        result = await self.session.execute(
            select(Permission).where(
                Permission.id == permission_id,
                Permission.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_module_action(self, module: str, action: str) -> Optional[Permission]:
        result = await self.session.execute(
            select(Permission).where(
                Permission.module == module,
                Permission.action == action,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, permission: Permission) -> Permission:
        self.session.add(permission)
        await self.session.flush()
        await self.session.refresh(permission)
        return permission

    async def get_role_permissions(self, role_id: uuid.UUID) -> List[Permission]:
        result = await self.session.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.is_deleted == False,
            )
        )
        return list(result.scalars().all())

    async def role_has_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        result = await self.session.execute(
            select(RolePermission.id).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
                RolePermission.is_deleted == False,
            )
        )
        return result.scalar_one_or_none() is not None

    async def assign_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> RolePermission:
        # Check for an existing soft-deleted record first (unique constraint on role_id+permission_id)
        result = await self.session.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Restore the soft-deleted record instead of inserting a duplicate
            existing.is_deleted = False
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        self.session.add(rp)
        await self.session.flush()
        await self.session.refresh(rp)
        return rp

    async def remove_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None:
        result = await self.session.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        rp = result.scalar_one_or_none()
        if rp:
            rp.is_deleted = True
            await self.session.flush()
