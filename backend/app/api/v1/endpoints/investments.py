"""Investments endpoints — portfolios, transactions, positions, market."""
import uuid
from datetime import date
from typing import Annotated, Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, get_user_group_ids
from app.services.investment_service import InvestmentService
from app.models.institution import InstitutionGroupLink
from app.models.group import Group
from sqlalchemy import select
from app.schemas.investment import (
    PortfolioCreate, PortfolioUpdate, PortfolioResponse,
    InvestmentTransactionCreate, InvestmentTransactionResponse,
    PortfolioPositionResponse, UpdatePositionPriceRequest, MarketPriceResponse
)

router = APIRouter(prefix="/investments", tags=["investments"])


class MarketSymbolAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    name: Optional[str] = None


# ------------------------------------------------------------------ #
# Portfolios
# ------------------------------------------------------------------ #

@router.get("/portfolios", response_model=List[PortfolioResponse])
async def list_portfolios(
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    group_id: Optional[uuid.UUID] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    portfolios = await svc.list_portfolios(
        current_user.tenant_id, group_id=group_id, active_only=active_only,
        skip=skip, limit=limit, group_ids=group_ids or None,
    )

    # Enrich with group_names from institution_group_links
    inst_ids = [p.institution_id for p in portfolios if p.institution_id]
    inst_group_names: dict = {}
    if inst_ids:
        rows = (await db.execute(
            select(InstitutionGroupLink.institution_id, Group.name)
            .join(Group, Group.id == InstitutionGroupLink.group_id)
            .where(InstitutionGroupLink.institution_id.in_(inst_ids))
        )).all()
        for row in rows:
            inst_group_names.setdefault(row.institution_id, []).append(row.name)

    for p in portfolios:
        if p.institution_id and p.institution_id in inst_group_names:
            p.group_names = inst_group_names[p.institution_id]

    return portfolios


@router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    body: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "create")),
):
    svc = InvestmentService(db)
    return await svc.create_portfolio(
        current_user.tenant_id, current_user.id, body.model_dump()
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    return await svc.get_portfolio(portfolio_id, current_user.tenant_id)


@router.patch("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: uuid.UUID,
    body: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "update")),
):
    svc = InvestmentService(db)
    return await svc.update_portfolio(
        portfolio_id, current_user.tenant_id, current_user.id,
        body.model_dump(exclude_none=True),
    )


# ------------------------------------------------------------------ #
# Transactions
# ------------------------------------------------------------------ #

@router.get("/portfolios/{portfolio_id}/transactions", response_model=List[InvestmentTransactionResponse])
async def list_transactions(
    portfolio_id: uuid.UUID,
    symbol: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    return await svc.list_transactions(
        portfolio_id, current_user.tenant_id,
        symbol=symbol, transaction_type=transaction_type,
        date_from=date_from, date_to=date_to,
        skip=skip, limit=limit,
    )


@router.post("/portfolios/{portfolio_id}/transactions", response_model=InvestmentTransactionResponse, status_code=201)
async def record_transaction(
    portfolio_id: uuid.UUID,
    body: InvestmentTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "create")),
):
    svc = InvestmentService(db)
    return await svc.record_transaction(
        portfolio_id, current_user.tenant_id, current_user.id, body.model_dump()
    )


@router.patch("/portfolios/{portfolio_id}/transactions/{tx_id}", response_model=InvestmentTransactionResponse)
async def update_transaction(
    portfolio_id: uuid.UUID,
    tx_id: uuid.UUID,
    body: InvestmentTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "update")),
):
    svc = InvestmentService(db)
    return await svc.update_transaction(
        tx_id, portfolio_id, current_user.tenant_id, current_user.id,
        body.model_dump(exclude_none=True),
    )


@router.delete("/portfolios/{portfolio_id}/transactions/{tx_id}", status_code=204)
async def delete_transaction(
    portfolio_id: uuid.UUID,
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "delete")),
):
    svc = InvestmentService(db)
    await svc.delete_transaction(
        tx_id, portfolio_id, current_user.tenant_id, current_user.id
    )


# ------------------------------------------------------------------ #
# Positions
# ------------------------------------------------------------------ #

@router.get("/positions", response_model=List[PortfolioPositionResponse])
async def list_all_positions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    return await svc.list_all_positions(current_user.tenant_id)


@router.get("/portfolios/{portfolio_id}/positions", response_model=List[PortfolioPositionResponse])
async def get_positions(
    portfolio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    return await svc.get_positions(portfolio_id, current_user.tenant_id)


@router.put("/portfolios/{portfolio_id}/positions/{symbol}/price")
async def update_position_price(
    portfolio_id: uuid.UUID,
    symbol: str,
    body: UpdatePositionPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "update")),
):
    svc = InvestmentService(db)
    return await svc.update_position_price(
        portfolio_id, current_user.tenant_id, symbol.upper(), body.current_price
    )


# ------------------------------------------------------------------ #
# Market
# ------------------------------------------------------------------ #

@router.get("/market", response_model=List[MarketPriceResponse])
async def list_market_prices(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "view")),
):
    svc = InvestmentService(db)
    return await svc.list_market_prices(current_user.tenant_id)


@router.post("/market", response_model=MarketPriceResponse, status_code=201)
async def add_market_symbol(
    body: MarketSymbolAdd,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "create")),
):
    svc = InvestmentService(db)
    return await svc.add_market_symbol(
        current_user.tenant_id, current_user.id,
        body.symbol, body.name
    )


@router.post("/market/refresh")
async def refresh_market_prices(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "update")),
):
    svc = InvestmentService(db)
    updated = await svc.refresh_market_prices(current_user.tenant_id)
    return {"updated": updated}


@router.delete("/market/{symbol}")
async def remove_market_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("investments", "delete")),
):
    svc = InvestmentService(db)
    await svc.remove_market_symbol(current_user.tenant_id, symbol)
    return {"message": f"Symbol {symbol} removed from market tracker"}
