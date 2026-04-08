"""Permission and role-permission management service."""
import uuid
from typing import List, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.repositories.role import PermissionRepository, RoleRepository
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleError

# Canonical system permissions: all (module, action) pairs Umay supports.
SYSTEM_PERMISSIONS: List[Dict[str, str]] = [
    # Users
    {"module": "users", "action": "view"},
    {"module": "users", "action": "create"},
    {"module": "users", "action": "update"},
    {"module": "users", "action": "delete"},
    {"module": "users", "action": "approve"},
    {"module": "users", "action": "export"},
    # Roles & Permissions
    {"module": "roles", "action": "view"},
    {"module": "roles", "action": "create"},
    {"module": "roles", "action": "update"},
    {"module": "roles", "action": "delete"},
    {"module": "permissions", "action": "view"},
    {"module": "permissions", "action": "assign"},
    # Groups
    {"module": "groups", "action": "view"},
    {"module": "groups", "action": "create"},
    {"module": "groups", "action": "update"},
    {"module": "groups", "action": "delete"},
    # Tenants
    {"module": "tenants", "action": "view"},
    {"module": "tenants", "action": "update"},
    # Accounts (Phase 2)
    {"module": "accounts", "action": "view"},
    {"module": "accounts", "action": "create"},
    {"module": "accounts", "action": "update"},
    {"module": "accounts", "action": "delete"},
    {"module": "accounts", "action": "export"},
    # Categories
    {"module": "categories", "action": "view"},
    {"module": "categories", "action": "create"},
    {"module": "categories", "action": "update"},
    {"module": "categories", "action": "delete"},
    # Transactions
    {"module": "transactions", "action": "view"},
    {"module": "transactions", "action": "create"},
    {"module": "transactions", "action": "update"},
    {"module": "transactions", "action": "delete"},
    {"module": "transactions", "action": "approve"},
    {"module": "transactions", "action": "export"},
    # Planned Payments
    {"module": "planned_payments", "action": "view"},
    {"module": "planned_payments", "action": "create"},
    {"module": "planned_payments", "action": "update"},
    {"module": "planned_payments", "action": "delete"},
    # Loans
    {"module": "loans", "action": "view"},
    {"module": "loans", "action": "create"},
    {"module": "loans", "action": "update"},
    {"module": "loans", "action": "delete"},
    {"module": "loans", "action": "export"},
    # Credit Cards
    {"module": "credit_cards", "action": "view"},
    {"module": "credit_cards", "action": "create"},
    {"module": "credit_cards", "action": "update"},
    {"module": "credit_cards", "action": "delete"},
    # Assets
    {"module": "assets", "action": "view"},
    {"module": "assets", "action": "create"},
    {"module": "assets", "action": "update"},
    {"module": "assets", "action": "delete"},
    # Investments
    {"module": "investments", "action": "view"},
    {"module": "investments", "action": "create"},
    {"module": "investments", "action": "update"},
    {"module": "investments", "action": "delete"},
    # Market watchlist
    {"module": "market", "action": "view"},
    {"module": "market", "action": "manage"},
    # Documents
    {"module": "documents", "action": "view"},
    {"module": "documents", "action": "create"},
    {"module": "documents", "action": "delete"},
    # Calendar
    {"module": "calendar", "action": "view"},
    {"module": "calendar", "action": "sync"},
    # Reports
    {"module": "reports", "action": "view"},
    {"module": "reports", "action": "export"},
    # Delete requests
    {"module": "delete_requests", "action": "create"},   # any user can request
    {"module": "delete_requests", "action": "review"},   # admin: approve/reject
    {"module": "delete_requests", "action": "view"},
    # License & System
    {"module": "license", "action": "view"},
    {"module": "license", "action": "manage"},
    {"module": "system", "action": "backup"},
    {"module": "system", "action": "restore"},
    {"module": "system", "action": "reset"},
    {"module": "audit", "action": "view"},
]


class PermissionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PermissionRepository(session)
        self.role_repo = RoleRepository(session)
        self.audit = AuditService(session)

    async def list_all(self) -> List[Permission]:
        """Return all system permissions."""
        return await self.repo.get_all()

    async def get_by_id(self, permission_id: uuid.UUID) -> Permission:
        perm = await self.repo.get_by_id(permission_id)
        if not perm:
            raise NotFoundError("Permission")
        return perm

    async def seed_system_permissions(
        self,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
    ) -> Dict[str, int]:
        """
        Idempotently seed all canonical system permissions.
        Returns counts of created and skipped entries.
        """
        created = 0
        skipped = 0

        for entry in SYSTEM_PERMISSIONS:
            existing = await self.repo.get_by_module_action(
                entry["module"], entry["action"]
            )
            if existing:
                skipped += 1
                continue

            perm = Permission(
                module=entry["module"],
                action=entry["action"],
                description=f"{entry['action'].capitalize()} access to {entry['module']}",
            )
            await self.repo.create(perm)
            created += 1

        if created > 0:
            await self.audit.log(
                action="SEED",
                module="permissions",
                actor_id=actor_id,
                actor_email=actor_email,
                after={"created": created, "skipped": skipped},
            )

        return {"created": created, "skipped": skipped}

    async def get_role_permissions(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> List[Permission]:
        """Return all permissions assigned to a role."""
        role = await self.role_repo.get_by_id_and_tenant(role_id, tenant_id)
        if not role:
            raise NotFoundError("Role")
        return await self.repo.get_role_permissions(role_id)

    async def assign_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
    ) -> None:
        """Assign a permission to a role. Idempotent."""
        role = await self.role_repo.get_by_id_and_tenant(role_id, tenant_id)
        if not role:
            raise NotFoundError("Role")
        if role.is_system:
            raise BusinessRuleError("System roles' permissions cannot be modified")

        perm = await self.repo.get_by_id(permission_id)
        if not perm:
            raise NotFoundError("Permission")

        already_assigned = await self.repo.role_has_permission(role_id, permission_id)
        if already_assigned:
            raise ConflictError("Permission is already assigned to this role")

        await self.repo.assign_permission(role_id, permission_id)
        await self.audit.log(
            action="ASSIGN_PERMISSION",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
            after={"permission_id": str(permission_id), "module": perm.module, "action": perm.action},
        )

    async def remove_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
    ) -> None:
        """Remove a permission from a role."""
        role = await self.role_repo.get_by_id_and_tenant(role_id, tenant_id)
        if not role:
            raise NotFoundError("Role")
        if role.is_system:
            raise BusinessRuleError("System roles' permissions cannot be modified")

        perm = await self.repo.get_by_id(permission_id)
        if not perm:
            raise NotFoundError("Permission")

        assigned = await self.repo.role_has_permission(role_id, permission_id)
        if not assigned:
            raise NotFoundError("Permission assignment")

        await self.repo.remove_permission(role_id, permission_id)
        await self.audit.log(
            action="REMOVE_PERMISSION",
            module="roles",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(role_id),
            before={"permission_id": str(permission_id), "module": perm.module, "action": perm.action},
        )

    async def get_user_permission_set(self, role_id: uuid.UUID) -> set[str]:
        """
        Return a set of 'module:action' strings for a given role.
        Used for fast in-request authorization checks.
        """
        permissions = await self.repo.get_role_permissions(role_id)
        return {f"{p.module}:{p.action}" for p in permissions}
