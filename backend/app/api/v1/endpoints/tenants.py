import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_superuser, get_current_user
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.common import PagedResponse
from app.services.tenant_service import TenantService
from app.models.user import User

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=PagedResponse[TenantResponse])
async def list_tenants(
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = TenantService(session)
    items, total = await service.list_tenants(
        offset=(page - 1) * page_size, limit=page_size
    )
    return PagedResponse.build(
        items=[TenantResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    body: TenantCreate,
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    service = TenantService(session)
    tenant = await service.create(
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return tenant


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    service = TenantService(session)
    return await service.get_by_id(current_user.tenant_id)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    service = TenantService(session)
    return await service.get_by_id(tenant_id)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    service = TenantService(session)
    tenant = await service.update(
        tenant_id=tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return tenant
