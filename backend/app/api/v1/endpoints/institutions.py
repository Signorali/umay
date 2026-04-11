"""Institutions endpoints."""
import uuid
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, get_user_group_ids
from app.services.institution_service import InstitutionService
from app.schemas.institution import (
    InstitutionCreate, InstitutionUpdate, InstitutionResponse,
    CommissionRuleCreate, CommissionRuleResponse,
    TaxRuleCreate, TaxRuleResponse,
)

router = APIRouter(prefix="/institutions", tags=["institutions"])


def _can_access_institution(inst, current_user, group_ids: list) -> bool:
    """Return True if the user may access this institution."""
    if current_user.is_tenant_admin or current_user.is_superuser:
        return True
    # If institution has no group links, everyone with view permission can see it
    if not getattr(inst, "group_ids", []):
        return True
    return any(gid in (group_ids or []) for gid in inst.group_ids)


@router.get("", response_model=List[InstitutionResponse])
async def list_institutions(
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    institution_type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "view")),
):
    is_admin = current_user.is_tenant_admin or current_user.is_superuser
    svc = InstitutionService(db)
    return await svc.list(
        current_user.tenant_id,
        institution_type=institution_type,
        active_only=active_only,
        skip=skip, limit=limit,
        group_ids=None if is_admin else group_ids,
    )


@router.post("", response_model=InstitutionResponse, status_code=201)
async def create_institution(
    body: InstitutionCreate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "create")),
):
    is_admin = current_user.is_tenant_admin or current_user.is_superuser
    data = body.model_dump()
    # Non-admins can only link to their own groups
    if not is_admin and data.get("group_ids"):
        invalid = [g for g in data["group_ids"] if g not in (group_ids or [])]
        if invalid:
            raise HTTPException(status_code=403, detail="Sadece kendi grubunuza kurum ekleyebilirsiniz.")
    # Auto-assign group if non-admin has no group specified
    if not is_admin and not data.get("group_ids") and group_ids:
        data["group_ids"] = [group_ids[0]]
    svc = InstitutionService(db)
    return await svc.create(current_user.tenant_id, current_user.id, data)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(
    institution_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "view")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return inst


@router.patch("/{institution_id}", response_model=InstitutionResponse)
async def update_institution(
    institution_id: uuid.UUID,
    body: InstitutionUpdate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "update")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return await svc.update(
        institution_id, current_user.tenant_id, current_user.id,
        body.model_dump(exclude_none=True),
    )


@router.delete("/{institution_id}", status_code=204)
async def delete_institution(
    institution_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "delete")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    await svc.delete(institution_id, current_user.tenant_id, current_user.id)


# ------------------------------------------------------------------ #
# Commission rules
# ------------------------------------------------------------------ #

@router.get("/{institution_id}/commission-rules", response_model=List[CommissionRuleResponse])
async def list_commission_rules(
    institution_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "view")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return await svc.list_commission_rules(institution_id, current_user.tenant_id)


@router.post("/{institution_id}/commission-rules", response_model=CommissionRuleResponse, status_code=201)
async def add_commission_rule(
    institution_id: uuid.UUID,
    body: CommissionRuleCreate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "update")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return await svc.add_commission_rule(
        institution_id, current_user.tenant_id, current_user.id, body.model_dump()
    )


@router.delete("/{institution_id}/commission-rules/{rule_id}", status_code=204)
async def delete_commission_rule(
    institution_id: uuid.UUID,
    rule_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "update")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    await svc.delete_commission_rule(institution_id, rule_id, current_user.tenant_id)


# ------------------------------------------------------------------ #
# Tax rules
# ------------------------------------------------------------------ #

@router.get("/{institution_id}/tax-rules", response_model=List[TaxRuleResponse])
async def list_tax_rules(
    institution_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "view")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return await svc.list_tax_rules(institution_id, current_user.tenant_id)


@router.post("/{institution_id}/tax-rules", response_model=TaxRuleResponse, status_code=201)
async def add_tax_rule(
    institution_id: uuid.UUID,
    body: TaxRuleCreate,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "update")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    return await svc.add_tax_rule(
        institution_id, current_user.tenant_id, current_user.id, body.model_dump()
    )


@router.delete("/{institution_id}/tax-rules/{rule_id}", status_code=204)
async def delete_tax_rule(
    institution_id: uuid.UUID,
    rule_id: uuid.UUID,
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("institutions", "update")),
):
    svc = InstitutionService(db)
    inst = await svc.get(institution_id, current_user.tenant_id)
    if not _can_access_institution(inst, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Bu kuruma erişim yetkiniz yok.")
    await svc.delete_tax_rule(institution_id, rule_id, current_user.tenant_id)
