import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    AssignPermissionRequest,
)
from app.schemas.common import PagedResponse, MessageResponse
from app.services.role_service import RoleService
from app.models.user import User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=PagedResponse[RoleResponse])
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all roles in the current tenant."""
    service = RoleService(session)
    items, total = await service.list_by_tenant(
        current_user.tenant_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PagedResponse.build(
        items=[RoleResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Create a new role."""
    service = RoleService(session)
    role = await service.create(
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return RoleResponse.model_validate(role)


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """List all system-defined permissions."""
    service = RoleService(session)
    permissions = await service.list_permissions()
    return [PermissionResponse.model_validate(p) for p in permissions]


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Get a specific role by ID."""
    service = RoleService(session)
    return await service.get_by_id(role_id, current_user.tenant_id)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Update a role."""
    service = RoleService(session)
    role = await service.update(
        role_id=role_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", response_model=MessageResponse)
async def delete_role(
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Soft-delete a role."""
    service = RoleService(session)
    await service.delete(
        role_id=role_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Role deleted successfully")


@router.get("/{role_id}/permissions", response_model=List[PermissionResponse])
async def get_role_permissions(
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Get permissions assigned to a role."""
    service = RoleService(session)
    permissions = await service.get_role_permissions(role_id, current_user.tenant_id)
    return [PermissionResponse.model_validate(p) for p in permissions]


@router.post("/{role_id}/permissions", response_model=MessageResponse, status_code=201)
async def assign_permission(
    role_id: uuid.UUID,
    body: AssignPermissionRequest,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Assign a permission to a role."""
    service = RoleService(session)
    await service.assign_permission(
        role_id=role_id,
        permission_id=body.permission_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Permission assigned successfully")


@router.delete("/{role_id}/permissions/{permission_id}", response_model=MessageResponse)
async def remove_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Remove a permission from a role."""
    service = RoleService(session)
    await service.remove_permission(
        role_id=role_id,
        permission_id=permission_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Permission removed successfully")
