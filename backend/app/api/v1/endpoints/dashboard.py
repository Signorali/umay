"""Dashboard endpoints."""
import uuid
from datetime import date
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_user_group_ids
from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardWidgetUpdate, DashboardWidgetResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = DashboardService(db)
    return await svc.get_dashboard(
        current_user.id, current_user.tenant_id,
        group_ids=group_ids or None,
        period_start=period_start, period_end=period_end,
    )


@router.get("/widgets")
async def list_widgets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = DashboardService(db)
    return await svc.list_widgets(current_user.id, current_user.tenant_id)


@router.put("/widgets/{widget_id}", response_model=DashboardWidgetResponse)
async def update_widget(
    widget_id: uuid.UUID,
    body: DashboardWidgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = DashboardService(db)
    return await svc.update_widget(
        widget_id, current_user.id, current_user.tenant_id,
        body.model_dump(exclude_none=True),
    )
