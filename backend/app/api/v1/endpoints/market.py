"""Market data endpoints."""
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.market_service import MarketService
from app.schemas.market import WatchlistItemCreate
from app.models.market import WatchlistItem

router = APIRouter(prefix="/market", tags=["market"])


class WatchlistPinUpdate(BaseModel):
    """Bulk update: which items are pinned and their display order."""
    pinned_ids: List[uuid.UUID] = []
    ordered_ids: List[uuid.UUID] = []   # full ordered list of all item IDs


@router.get("/watchlist")
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    svc = MarketService(db)
    return await svc.get_watchlist(current_user.id, current_user.tenant_id)


@router.post("/watchlist", status_code=201)
async def add_to_watchlist(
    body: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "create")),
):
    svc = MarketService(db)
    return await svc.add_to_watchlist(
        current_user.tenant_id, current_user.id,
        {**body.model_dump(), "symbol": body.symbol.upper()},
    )


@router.delete("/watchlist/{item_id}", status_code=204)
async def remove_from_watchlist(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "delete")),
):
    svc = MarketService(db)
    await svc.remove_from_watchlist(item_id, current_user.tenant_id)


@router.post("/watchlist/refresh", status_code=200)
async def refresh_watchlist_prices(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    svc = MarketService(db)
    return await svc.refresh_prices_for_user(current_user.id, current_user.tenant_id)


@router.put("/watchlist/pins", status_code=200)
async def update_watchlist_pins(
    body: WatchlistPinUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    """
    Persist per-user pinned state and display order in watchlist_user_pins table.
    """
    from sqlalchemy import text
    pinned_set = set(body.pinned_ids)
    updated = 0
    for idx, item_id in enumerate(body.ordered_ids):
        is_pinned = item_id in pinned_set
        await db.execute(
            text("""
                INSERT INTO watchlist_user_pins (user_id, item_id, is_pinned, display_order)
                VALUES (:user_id, :item_id, :is_pinned, :display_order)
                ON CONFLICT (user_id, item_id) DO UPDATE
                  SET is_pinned = EXCLUDED.is_pinned,
                      display_order = EXCLUDED.display_order,
                      updated_at = now()
            """),
            {"user_id": current_user.id, "item_id": item_id,
             "is_pinned": is_pinned, "display_order": idx},
        )
        updated += 1
    await db.commit()
    return {"updated": updated}


@router.get("/tefas/search")
async def search_tefas_funds(
    q: str = Query(..., min_length=2, max_length=50),
    fund_type: str = Query("YAT"),
    current_user=Depends(require_permission("market", "view")),
):
    """TEFAS'ta fon ara. fund_type: YAT | EMK | BYF"""
    from app.services.tefas_service import search_funds
    return await search_funds(q, fund_type)


@router.get("/prices/current")
async def get_current_prices(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. USDTRY,EURTRY"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    """Return latest cached price snapshot for each requested symbol."""
    svc = MarketService(db)
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    cached = await svc._get_cached_prices(symbol_list)
    return {
        sym: {"price": float(snap.price), "currency": snap.currency, "snapshot_at": snap.snapshot_at.isoformat()}
        for sym, snap in cached.items()
    }


@router.get("/prices/{symbol}/history")
async def get_price_history(
    symbol: str,
    from_dt: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    svc = MarketService(db)
    return await svc.get_price_history(symbol.upper(), from_dt=from_dt, limit=limit)
