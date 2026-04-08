"""
Audit Log endpoints — read-only access to the immutable audit trail.

GET  /audit              → paginated, filtered audit log list (admin)
GET  /audit/security     → security-sensitive events only
GET  /audit/{record_id}  → history of a specific record in a module
"""
import uuid
from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.schemas.audit import AuditLogOut, AuditLogListOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditLogListOut)
async def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    module: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor_id: Optional[uuid.UUID] = Query(None),
    record_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List audit logs with optional filters. Scoped to current user's tenant."""
    repo = AuditRepository(session)
    items, total = await repo.list(
        tenant_id=current_user.tenant_id,
        module=module,
        action=action,
        actor_id=actor_id,
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AuditLogListOut(
        items=[AuditLogOut.model_validate(i) for i in items],
        total=total,
    )


@router.get("/security", response_model=AuditLogListOut)
async def list_security_events(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """Return security-sensitive events: logins, permission changes, resets, etc."""
    repo = AuditRepository(session)
    items = await repo.list_security_events(
        tenant_id=current_user.tenant_id,
        limit=limit,
    )
    return AuditLogListOut(
        items=[AuditLogOut.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/record/{module}/{record_id}", response_model=AuditLogListOut)
async def record_history(
    module: str,
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    """Get the full audit history for a specific record (e.g. a transaction)."""
    repo = AuditRepository(session)
    items = await repo.list_for_record(
        module=module,
        record_id=record_id,
        tenant_id=current_user.tenant_id,
        limit=limit,
    )
    return AuditLogListOut(
        items=[AuditLogOut.model_validate(i) for i in items],
        total=len(items),
    )
