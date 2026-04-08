"""Permission management endpoints."""
import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_superuser, get_current_tenant_admin
from app.models.user import User
from app.services.permission_service import PermissionService
from app.schemas.role import PermissionResponse, AssignPermissionRequest

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=List[PermissionResponse])
async def list_permissions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List all system-defined permissions."""
    svc = PermissionService(session)
    return await svc.list_all()


@router.post("/seed", status_code=200)
async def seed_permissions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_superuser)],
):
    """
    Seed all canonical system permissions into the database.
    Idempotent — safe to call multiple times.
    Superuser only.
    """
    svc = PermissionService(session)
    result = await svc.seed_system_permissions(
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    return {
        "message": "Permission seed complete",
        "created": result["created"],
        "skipped": result["skipped"],
    }


@router.get("/roles/{role_id}", response_model=List[PermissionResponse])
async def get_role_permissions(
    role_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
):
    """Get all permissions assigned to a role."""
    svc = PermissionService(session)
    return await svc.get_role_permissions(role_id, current_user.tenant_id)


@router.post("/roles/{role_id}/assign", status_code=201)
async def assign_permission(
    role_id: uuid.UUID,
    body: AssignPermissionRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
):
    """Assign a permission to a role."""
    async with session.begin():
        svc = PermissionService(session)
        await svc.assign_permission(
            role_id=role_id,
            permission_id=body.permission_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    return {"message": "Permission assigned"}


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=200)
async def remove_permission(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
):
    """Remove a permission from a role."""
    async with session.begin():
        svc = PermissionService(session)
        await svc.remove_permission(
            role_id=role_id,
            permission_id=permission_id,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    return {"message": "Permission removed"}
