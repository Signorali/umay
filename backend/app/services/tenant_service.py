import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.services.audit_service import AuditService
from app.core.exceptions import ConflictError, NotFoundError


class TenantService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TenantRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        data: TenantCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Tenant:
        if await self.repo.slug_exists(data.slug):
            raise ConflictError(f"Tenant with slug '{data.slug}' already exists")

        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            contact_email=data.contact_email,
            base_currency=data.base_currency,
            timezone=data.timezone,
            locale=data.locale,
        )
        tenant = await self.repo.create(tenant)

        await self.audit.log(
            action="CREATE",
            module="tenants",
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tenant.id),
            after={"name": tenant.name, "slug": tenant.slug},
        )
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.repo.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant")
        return tenant

    async def get_by_slug(self, slug: str) -> Tenant:
        tenant = await self.repo.get_by_slug(slug)
        if not tenant:
            raise NotFoundError("Tenant")
        return tenant

    async def list_tenants(self, offset: int = 0, limit: int = 20) -> Tuple[List[Tenant], int]:
        return await self.repo.list_all(offset=offset, limit=limit)

    async def update(
        self,
        tenant_id: uuid.UUID,
        data: TenantUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Tenant:
        tenant = await self.get_by_id(tenant_id)
        before = {"name": tenant.name, "is_active": tenant.is_active}

        update_fields = data.model_dump(exclude_none=True)
        tenant = await self.repo.update(tenant, **update_fields)

        await self.audit.log(
            action="UPDATE",
            module="tenants",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(tenant_id),
            before=before,
            after=update_fields,
        )
        return tenant

    async def mark_setup_complete(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.get_by_id(tenant_id)
        tenant = await self.repo.update(tenant, is_setup_complete=True)
        await self.audit.log(
            action="SETUP_COMPLETE",
            module="tenants",
            tenant_id=tenant_id,
            record_id=str(tenant_id),
        )
        return tenant
