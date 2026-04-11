"""
Period Lock endpoints — lock/unlock accounting periods.

Rules:
  - GET /period-lock               → list locked periods (any authenticated user)
  - POST /period-lock/{year}/{month}   → lock a period (admin only)
  - DELETE /period-lock/{year}/{month} → unlock a period (admin only)
"""
from typing import Annotated, List
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.models.user import User
from app.services.period_lock_service import PeriodLockService

router = APIRouter(prefix="/period-lock", tags=["period-lock"])


@router.get("", response_model=List[str])
async def get_locked_periods(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """List all locked accounting periods (YYYY-MM format)."""
    svc = PeriodLockService(session)
    return await svc.get_locked_periods()


@router.post("/{year}/{month}", response_model=List[str])
async def lock_period(
    year: int = Path(..., ge=2000, le=2099),
    month: int = Path(..., ge=1, le=12),
    current_user: Annotated[User, Depends(get_current_tenant_admin)] = None,
    session: AsyncSession = Depends(get_db),
):
    """
    Lock an accounting period. Once locked, no transactions can be created,
    updated or deleted for that month. Audit logged.
    """
    svc = PeriodLockService(session)
    locked = await svc.lock_period(
        year=year,
        month=month,
        actor_id=current_user.id,
        actor_email=current_user.email,
        tenant_id=current_user.tenant_id,
    )
    await session.commit()
    return locked


@router.delete("/{year}/{month}", response_model=List[str])
async def unlock_period(
    year: int = Path(..., ge=2000, le=2099),
    month: int = Path(..., ge=1, le=12),
    current_user: Annotated[User, Depends(get_current_tenant_admin)] = None,
    session: AsyncSession = Depends(get_db),
):
    """Unlock a previously locked period. Audit logged."""
    svc = PeriodLockService(session)
    locked = await svc.unlock_period(
        year=year,
        month=month,
        actor_id=current_user.id,
        actor_email=current_user.email,
        tenant_id=current_user.tenant_id,
    )
    await session.commit()
    return locked
