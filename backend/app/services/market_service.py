"""Market service — single source of truth: price_snapshots table."""
import uuid
import re
import ast
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.market import WatchlistItem, PriceSnapshot
from app.repositories.market import PriceSnapshotRepository, WatchlistRepository
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


def _evaluate_formula(formula: str, prices: dict) -> float:
    """
    Safely evaluate a formula like "USDTRY * GOLD / 31.1 + 5".
    Symbol names are looked up in prices dict (upper-cased keys).
    Only numeric literals and +, -, *, / operations are allowed.
    """
    tokens = re.findall(r'[A-Z][A-Z0-9:._\-]*|[\d]+(?:\.[\d]+)?|[+\-*/()]', formula.upper())
    if not tokens:
        raise ValueError("Boş formül")

    resolved = []
    for token in tokens:
        if re.match(r'^[A-Z][A-Z0-9:._\-]*$', token):
            price = prices.get(token)
            if price is None:
                raise ValueError(f"Fiyat bulunamadı: {token}")
            resolved.append(str(float(price)))
        else:
            resolved.append(token)

    expr = ' '.join(resolved)

    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise ValueError(f"Geçersiz formül sözdizimi: {e}")

    _SAFE_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
    )
    for node in ast.walk(tree):
        if not isinstance(node, _SAFE_NODES):
            raise ValueError(f"Geçersiz formül: {type(node).__name__}")

    result = eval(compile(tree, '<formula>', 'eval'))  # noqa: S307
    return float(result)


async def _fetch_price(symbol: str, source: str) -> Optional[dict]:
    """Fetch price from the appropriate source."""
    if source == "google_finance":
        return await MarketDataService.fetch_google_finance_price(symbol)
    if source.startswith("tefas"):
        # source format: "tefas_YAT" | "tefas_EMK" | "tefas_BYF"
        fund_type = source.split("_", 1)[1] if "_" in source else "YAT"
        from app.services.tefas_service import get_fund_price
        return await get_fund_price(symbol, fund_type)
    return None


class MarketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshot_repo = PriceSnapshotRepository(db)
        self.watchlist_repo = WatchlistRepository(db)

    async def _get_cached_prices(self, symbols: List[str]) -> dict:
        """Return {symbol: PriceSnapshot} from price_snapshots table."""
        return await self.snapshot_repo.get_latest([s.upper() for s in symbols])

    async def _fetch_and_save_prices(self, items: List[Tuple[str, str]]) -> dict:
        """
        Fetch fresh prices for a list of (symbol, source) tuples.
        Save to price_snapshots. Return {symbol: {price, currency, change_percent, trend, ...}}.
        """
        results = {}
        now = datetime.now(timezone.utc)

        for symbol, source in items:
            data = await _fetch_price(symbol, source)
            if data:
                snap = PriceSnapshot(
                    symbol=symbol.upper(),
                    price=data["price"],
                    currency=data["currency"],
                    change_percent=data.get("change_percent"),
                    trend=data.get("trend"),
                    is_realtime=True,
                    snapshot_at=now,
                    source_label=source,
                )
                self.db.add(snap)
                results[symbol.upper()] = {
                    "price": float(data["price"]),
                    "currency": data["currency"],
                    "change_percent": float(data["change_percent"]) if data.get("change_percent") else None,
                    "trend": data.get("trend"),
                    "snapshot_at": now.isoformat(),
                }
            else:
                logger.warning(f"No price fetched for {symbol} ({source})")

        if results:
            await self.db.commit()

        return results

    # ------------------------------------------------------------------ #
    # Watchlist
    # ------------------------------------------------------------------ #

    async def get_watchlist(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> list:
        """Return tenant-wide watchlist items with per-user pin preferences."""
        from sqlalchemy import text
        items = await self.watchlist_repo.get_by_tenant(tenant_id)
        if not items:
            return []

        # Load this user's pin preferences
        pin_rows = await self.db.execute(
            text("SELECT item_id, is_pinned, display_order FROM watchlist_user_pins WHERE user_id = :uid"),
            {"uid": user_id},
        )
        user_pins = {str(row.item_id): row for row in pin_rows}

        symbols = [i.symbol.upper() for i in items]
        cached = await self._get_cached_prices(symbols)

        result = []
        for item in items:
            sym = item.symbol.upper()
            snap = cached.get(sym)
            pin = user_pins.get(str(item.id))
            result.append({
                "id": str(item.id),
                "symbol": item.symbol,
                "label": item.label or item.symbol,
                "source": item.source,
                "formula": item.formula,
                "is_formula": item.source == "formula",
                "is_pinned": pin.is_pinned if pin else False,
                "display_order": pin.display_order if pin else 9999,
                "price": float(snap.price) if snap else None,
                "currency": snap.currency if snap else (
                    "FORMULA" if item.source == "formula"
                    else "TRY" if item.source.startswith("tefas")
                    else "USD"
                ),
                "change_percent": float(snap.change_percent) if snap and snap.change_percent else None,
                "trend": snap.trend if snap else None,
                "snapshot_at": snap.snapshot_at.isoformat() if snap else None,
            })
        # Sort by user's own display_order, then symbol
        result.sort(key=lambda x: (x["display_order"], x["symbol"]))
        return result

    async def _evaluate_and_save_formula(self, symbol: str, formula: str) -> Optional[dict]:
        """Evaluate formula using latest cached prices and save a snapshot."""
        # Find all symbol references in formula
        sym_tokens = re.findall(r'[A-Z][A-Z0-9:._\-]*', formula.upper())
        sym_tokens = [s for s in sym_tokens if not re.match(r'^\d', s)]
        cached = await self._get_cached_prices(sym_tokens)
        prices = {s: float(snap.price) for s, snap in cached.items()}

        try:
            value = _evaluate_formula(formula, prices)
        except ValueError as e:
            logger.warning(f"Formula eval error for {symbol}: {e}")
            return None

        now = datetime.now(timezone.utc)
        snap = PriceSnapshot(
            symbol=symbol.upper(),
            price=Decimal(str(round(value, 8))),
            currency="FORMULA",
            change_percent=None,
            trend=None,
            is_realtime=True,
            snapshot_at=now,
            source_label="formula",
        )
        self.db.add(snap)
        await self.db.commit()
        return {
            "price": value,
            "currency": "FORMULA",
            "change_percent": None,
            "trend": None,
            "snapshot_at": now.isoformat(),
        }

    async def add_to_watchlist(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict
    ) -> dict:
        """Add symbol to watchlist. Immediately fetch and cache its price."""
        symbol = data["symbol"].upper()
        source = data.get("source", "google_finance")
        formula = data.get("formula")

        # Check duplicate (tenant-wide)
        existing = await self.watchlist_repo.get_by_tenant(tenant_id)
        for e in existing:
            if e.symbol.upper() == symbol:
                raise HTTPException(status_code=409, detail=f"{symbol} zaten izleme listenizde.")

        item = await self.watchlist_repo.add(tenant_id, user_id, data)
        await self.db.commit()
        await self.db.refresh(item)

        price_data: dict = {}
        if source == "formula" and formula:
            price_data = await self._evaluate_and_save_formula(symbol, formula) or {}
        else:
            fetched = await self._fetch_and_save_prices([(symbol, source)])
            price_data = fetched.get(symbol, {})

        return {
            "id": str(item.id),
            "symbol": symbol,
            "label": item.label or symbol,
            "source": source,
            "formula": formula,
            "price": price_data.get("price"),
            "currency": price_data.get("currency", "TRY" if source == "formula" else "USD"),
            "change_percent": price_data.get("change_percent"),
            "trend": price_data.get("trend"),
            "snapshot_at": price_data.get("snapshot_at"),
        }

    async def remove_from_watchlist(self, item_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.models.investment import InvestmentTransaction
        item = await self.watchlist_repo.get_item(item_id, tenant_id)
        if not item:
            raise HTTPException(status_code=404, detail="Sembol bulunamadı.")
        symbol = item.symbol.upper()
        await self.db.delete(item)
        await self.db.flush()

        # Başka kullanıcı izlemiyor mu?
        other = await self.db.execute(
            select(WatchlistItem).where(
                WatchlistItem.symbol == symbol,
                WatchlistItem.is_deleted == False,
            ).limit(1)
        )
        still_watched = other.scalars().first() is not None

        # Yatırım işlemi var mı?
        tx = await self.db.execute(
            select(InvestmentTransaction).where(
                InvestmentTransaction.symbol == symbol
            ).limit(1)
        )
        has_transactions = tx.scalars().first() is not None

        if not still_watched and not has_transactions:
            await self.db.execute(
                select(PriceSnapshot).where(PriceSnapshot.symbol == symbol)
            )
            from sqlalchemy import delete as sa_delete
            await self.db.execute(
                sa_delete(PriceSnapshot).where(PriceSnapshot.symbol == symbol)
            )

        await self.db.commit()

    async def refresh_prices_for_user(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict:
        """Refresh prices for all watchlist symbols."""
        items = await self.watchlist_repo.get_by_tenant(tenant_id)
        if not items:
            return {"updated": 0}
        # Fetch real symbols first
        real_items = [(i.symbol.upper(), i.source) for i in items if i.source != "formula"]
        formula_items = [i for i in items if i.source == "formula" and i.formula]
        fetched = await self._fetch_and_save_prices(real_items) if real_items else {}
        # Then evaluate formula symbols (they depend on real prices)
        for fi in formula_items:
            result = await self._evaluate_and_save_formula(fi.symbol.upper(), fi.formula)
            if result:
                fetched[fi.symbol.upper()] = result
        return {"updated": len(fetched), "symbols": list(fetched.keys())}

    # ------------------------------------------------------------------ #
    # Background job (called by worker every 15 min)
    # ------------------------------------------------------------------ #

    async def refresh_all_prices(self) -> dict:
        """Refresh prices for ALL watchlist symbols across all users."""
        q = select(WatchlistItem.symbol, WatchlistItem.source, WatchlistItem.formula).where(
            WatchlistItem.is_deleted == False
        ).distinct()
        rows = list((await self.db.execute(q)).all())
        if not rows:
            return {"updated": 0}

        # Fetch real symbols first
        real = [(r[0].upper(), r[1]) for r in rows if r[1] != "formula"]
        formula_rows = [(r[0].upper(), r[2]) for r in rows if r[1] == "formula" and r[2]]
        fetched = await self._fetch_and_save_prices(real) if real else {}
        # Then evaluate formula symbols
        for sym, formula in formula_rows:
            result = await self._evaluate_and_save_formula(sym, formula)
            if result:
                fetched[sym] = result
        return {"updated": len(fetched), "symbols": list(fetched.keys())}

    async def get_price_history(
        self, symbol: str, from_dt=None, limit: int = 100
    ) -> list:
        history = await self.snapshot_repo.get_history(symbol, from_dt, limit)
        return [
            {
                "price": float(s.price),
                "currency": s.currency,
                "snapshot_at": s.snapshot_at.isoformat(),
            }
            for s in history
        ]
