import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.models.permission import Permission
from app.repositories.role import RoleRepository, PermissionRepository
from app.schemas.role import RoleCreate, RoleUpdate, PermissionCreate
from app.services.audit_service import AuditService
from app.core.exceptions import ConflictError, NotFoundError, BusinessRuleError

# System-defined permissions seeded on first setup
SYSTEM_PERMISSIONS: List[dict] = [
    # Users module
    {"module": "users", "action": "view", "description": "View users"},
    {"module": "users", "action": "create", "description": "Create users"},
    {"module": "users", "action": "update", "description": "Update users"},
    {"module": "users", "action": "delete", "description": "Delete users"},
    {"module": "users", "action": "approve", "description": "Approve user actions"},
    {"module": "users", "action": "export", "description": "Export users"},
    # Groups module
    {"module": "groups", "action": "view", "description": "View groups"},
    {"module": "groups", "action": "create", "description": "Create groups"},
    {"module": "groups", "action": "update", "description": "Update groups"},
    {"module": "groups", "action": "delete", "description": "Delete groups"},
    # Roles module
    {"module": "roles", "action": "view", "description": "View roles"},
    {"module": "roles", "action": "create", "description": "Create roles"},
    {"module": "roles", "action": "update", "description": "Update roles"},
    {"module": "roles", "action": "delete", "description": "Delete roles"},
    # Audit module
    {"module": "audit", "action": "view", "description": "View audit logs"},
    {"module": "audit", "action": "export", "description": "Export audit logs"},
]


class RoleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = RoleRepository(session)
        self.perm_repo = PermissionRepository(session)
        self.audit = AuditService(session)

    async def seed_permissions(self) -> List[Permission]:
        """Ensure all system permissions exist. Called during setup wizard."""
        created = []
        for p in SYSTEM_PERMISSIONS:
            existing = await self.perm_repo.get_by_module_action(p["module"], p["action"])
            if not existing:
                permission = Permission(
                    module=p["module"],
                    action=p["action"],
                    description=p["description"],
                )
                permission = await self.perm_repo.create(permission)
                created.append(permission)
        return created

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: RoleCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Role:
        if await self.repo.name_exists(data.name, tenant_id):
            raise ConflictError(f"Role '{data.name}' already exists in this tenant")

        role = Role(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        role = await self.repo.create(role)

        await self.audit.log(
            action="CREATE",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role.id),
            after={"name": role.name},
        )
        return role

    async def get_by_id(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Role:
        role = await self.repo.get_by_id_and_tenant(role_id, tenant_id)
        if not role:
            raise NotFoundError("Role")
        return role

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> Tuple[List[Role], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit)

    async def update(
        self,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: RoleUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Role:
        role = await self.get_by_id(role_id, tenant_id)

        if role.is_system:
            raise BusinessRuleError("System roles cannot be modified")

        before = {"name": role.name, "is_active": role.is_active}

        if data.name and data.name != role.name:
            if await self.repo.name_exists(data.name, tenant_id):
                raise ConflictError(f"Role '{data.name}' already exists in this tenant")

        update_fields = data.model_dump(exclude_none=True)
        role = await self.repo.update(role, **update_fields)

        await self.audit.log(
            action="UPDATE",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
            before=before,
            after=update_fields,
        )
        return role

    async def delete(
        self,
        role_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        role = await self.get_by_id(role_id, tenant_id)
        if role.is_system:
            raise BusinessRuleError("System roles cannot be deleted")

        await self.repo.soft_delete(role)
        await self.audit.log(
            action="DELETE",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
        )

    async def list_permissions(self) -> List[Permission]:
        return await self.perm_repo.get_all()

    async def get_role_permissions(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> List[Permission]:
        await self.get_by_id(role_id, tenant_id)  # validates access
        return await self.perm_repo.get_role_permissions(role_id)

    async def assign_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        role = await self.get_by_id(role_id, tenant_id)
        permission = await self.perm_repo.get_by_id(permission_id)
        if not permission:
            raise NotFoundError("Permission")

        # No conflict check needed — assign_permission handles soft-delete restore
        await self.perm_repo.assign_permission(role_id, permission_id)
        await self.audit.log(
            action="PERMISSION_ASSIGN",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
            after={"permission_id": str(permission_id)},
        )

    async def remove_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        await self.get_by_id(role_id, tenant_id)  # validates access
        await self.perm_repo.remove_permission(role_id, permission_id)
        await self.audit.log(
            action="PERMISSION_REMOVE",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
            after={"permission_id": str(permission_id)},
        )
