import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.group import Group
from app.models.user import UserGroup
from app.repositories.group import GroupRepository
from app.schemas.group import GroupCreate, GroupUpdate
from app.services.audit_service import AuditService
from app.core.exceptions import ConflictError, NotFoundError, BusinessRuleError, ForbiddenError


class GroupService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GroupRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: GroupCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Group:
        if await self.repo.name_exists(data.name, tenant_id):
            raise ConflictError(f"Group '{data.name}' already exists in this tenant")

        group = Group(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        group = await self.repo.create(group)

        await self.audit.log(
            action="CREATE",
            module="groups",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(group.id),
            after={"name": group.name},
        )
        return group

    async def get_by_id(self, group_id: uuid.UUID, tenant_id: uuid.UUID) -> Group:
        group = await self.repo.get_by_id_and_tenant(group_id, tenant_id)
        if not group:
            raise NotFoundError("Group")
        return group

    async def get_accessible(
        self,
        group_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool,
    ) -> Group:
        group = await self.get_by_id(group_id, tenant_id)
        if not is_admin:
            in_group = await self.repo.is_user_in_group(user_id, group_id)
            if not in_group:
                raise ForbiddenError("You do not have access to this group")
        return group

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Group], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit)

    async def list_by_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Group], int]:
        return await self.repo.get_by_user(user_id, tenant_id, offset=offset, limit=limit)

    async def get_user_group_ids(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> List[uuid.UUID]:
        return await self.repo.get_user_group_ids(user_id, tenant_id)

    async def update(
        self,
        group_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: GroupUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Group:
        group = await self.get_by_id(group_id, tenant_id)
        before = {"name": group.name, "is_active": group.is_active}

        if data.name and data.name != group.name:
            if await self.repo.name_exists(data.name, tenant_id):
                raise ConflictError(f"Group '{data.name}' already exists in this tenant")

        update_fields = data.model_dump(exclude_none=True)
        group = await self.repo.update(group, **update_fields)

        await self.audit.log(
            action="UPDATE",
            module="groups",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(group_id),
            before=before,
            after=update_fields,
        )
        return group

    async def delete(
        self,
        group_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        group = await self.get_by_id(group_id, tenant_id)
        if getattr(group, "is_system", False):
            raise BusinessRuleError("System groups cannot be deleted")

        await self.repo.soft_delete(group)
        await self.audit.log(
            action="DELETE",
            module="groups",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(group_id),
        )

    async def add_member(
        self,
        group_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self.get_by_id(group_id, tenant_id)
        already = await self.repo.is_user_in_group(user_id, group_id)
        if already:
            return
        ug = UserGroup(user_id=user_id, group_id=group_id)
        self.session.add(ug)

    async def remove_member(
        self,
        group_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        await self.get_by_id(group_id, tenant_id)
        result = await self.session.execute(
            select(UserGroup).where(
                UserGroup.user_id == user_id,
                UserGroup.group_id == group_id,
            )
        )
        ug = result.scalar_one_or_none()
        if ug:
            await self.session.delete(ug)
