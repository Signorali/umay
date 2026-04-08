"""Report endpoints."""
import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/income-expense")
async def income_expense_report(
    period_start: date = Query(...),
    period_end: date = Query(...),
    group_id: Optional[uuid.UUID] = Query(None),
    category_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.income_expense_report(
        current_user.tenant_id, period_start, period_end,
        group_id=group_id, category_id=category_id,
    )


@router.get("/account-movement")
async def account_movement_report(
    account_id: uuid.UUID = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.account_movement_report(
        account_id, current_user.tenant_id, period_start, period_end
    )


@router.get("/category-breakdown")
async def category_breakdown(
    period_start: date = Query(...),
    period_end: date = Query(...),
    transaction_type: str = Query("EXPENSE"),
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.category_breakdown(
        current_user.tenant_id, period_start, period_end,
        transaction_type=transaction_type, group_id=group_id,
    )


@router.get("/cash-flow")
async def cash_flow_projection(
    months_ahead: int = Query(3, ge=1, le=12),
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.cash_flow_projection(
        current_user.tenant_id, months_ahead=months_ahead, group_id=group_id
    )


@router.get("/loans")
async def loan_report(
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.loan_report(current_user.tenant_id, group_id=group_id)


@router.get("/credit-cards")
async def credit_card_report(
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    svc = ReportService(db)
    return await svc.credit_card_report(current_user.tenant_id, group_id=group_id)


@router.get("/assets")
async def asset_report(
    group_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    """Asset portfolio: purchase value, current value, realized & unrealized gain/loss."""
    svc = ReportService(db)
    return await svc.asset_report(current_user.tenant_id, group_id=group_id)


@router.get("/investment-performance")
async def investment_performance_report(
    portfolio_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("reports", "view")),
):
    """Investment P&L: realized gains, dividend/interest income, open positions."""
    svc = ReportService(db)
    return await svc.investment_performance_report(
        current_user.tenant_id, portfolio_id=portfolio_id
    )
