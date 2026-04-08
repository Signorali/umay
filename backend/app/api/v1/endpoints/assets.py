"""Assets endpoints."""
import uuid
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, get_user_group_ids
from app.services.asset_service import AssetService
from app.schemas.asset import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetDisposeRequest, AssetValuationCreate, AssetValuationResponse,
)

router = APIRouter(prefix="/assets", tags=["assets"])


def _can_access_asset(asset, current_user, group_ids: list) -> bool:
    """Return True if the current user may access this asset."""
    if current_user.is_tenant_admin or current_user.is_superuser:
        return True
    if asset.group_id is None:
        return True
    return asset.group_id in (group_ids or [])


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    group_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "view")),
):
    svc = AssetService(db)
    return await svc.list_assets(
        current_user.tenant_id, group_id=group_id,
        status=status, asset_type=asset_type, skip=skip, limit=limit,
        group_ids=group_ids or None,
    )


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    body: AssetCreate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "create")),
):
    is_admin = current_user.is_tenant_admin or current_user.is_superuser
    if not is_admin:
        if body.group_id and body.group_id not in (group_ids or []):
            raise HTTPException(status_code=403, detail="Bu gruba varlık ekleyemezsiniz.")
        if not body.group_id and group_ids:
            # Auto-assign first group if user belongs to exactly one group
            data = body.model_dump()
            data["group_id"] = group_ids[0]
        else:
            data = body.model_dump()
    else:
        data = body.model_dump()
    svc = AssetService(db)
    return await svc.create_asset(current_user.tenant_id, current_user.id, data)


@router.get("/summary")
async def portfolio_summary(
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "view")),
):
    is_admin = current_user.is_tenant_admin or current_user.is_superuser
    # Non-admins can only see their own groups' summary
    effective_group_ids = None if is_admin else (group_ids or [])
    svc = AssetService(db)
    return await svc.get_portfolio_summary(
        current_user.tenant_id, group_id=group_id,
        group_ids=effective_group_ids,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "view")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    return asset


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "update")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    return await svc.update_asset(
        asset_id, current_user.tenant_id, current_user.id,
        body.model_dump(exclude_none=True),
    )


@router.post("/{asset_id}/dispose", response_model=AssetResponse)
async def dispose_asset(
    asset_id: uuid.UUID,
    body: AssetDisposeRequest,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "update")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    return await svc.dispose_asset(
        asset_id, current_user.tenant_id, current_user.id,
        sale_date=body.sale_date,
        sale_value=body.sale_value,
        sale_notes=body.sale_notes,
        is_sold=body.is_sold,
        target_account_id=body.target_account_id,
    )


@router.get("/{asset_id}/valuations", response_model=List[AssetValuationResponse])
async def get_valuations(
    asset_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "view")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    return await svc.get_valuations(asset_id, current_user.tenant_id)


@router.post("/{asset_id}/valuations", response_model=AssetValuationResponse, status_code=201)
async def add_valuation(
    asset_id: uuid.UUID,
    body: AssetValuationCreate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "update")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    return await svc.add_valuation(
        asset_id, current_user.tenant_id, current_user.id, body.model_dump()
    )


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("assets", "delete")),
):
    svc = AssetService(db)
    asset = await svc.get_asset(asset_id, current_user.tenant_id)
    if not _can_access_asset(asset, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu varlığa erişim yetkiniz yok.")
    await svc.delete_asset(asset_id, current_user.tenant_id, current_user.id)
