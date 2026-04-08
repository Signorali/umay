"""Market data repositories — providers, price snapshots, watchlists."""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import MarketProvider, PriceSnapshot, WatchlistItem


class MarketProviderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> List[MarketProvider]:
        q = select(MarketProvider).where(
            MarketProvider.is_active == True,
            MarketProvider.is_deleted == False,
        ).order_by(MarketProvider.priority.desc())
        return list((await self.db.execute(q)).scalars().all())

    async def get_by_name(self, name: str) -> Optional[MarketProvider]:
        q = select(MarketProvider).where(
            MarketProvider.name == name,
            MarketProvider.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def create(self, data: dict) -> MarketProvider:
        obj = MarketProvider(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def list_all(self, skip: int = 0, limit: int = 50) -> List[MarketProvider]:
        q = select(MarketProvider).where(
            MarketProvider.is_deleted == False
        ).order_by(MarketProvider.priority.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())


class PriceSnapshotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: dict) -> PriceSnapshot:
        obj = PriceSnapshot(**data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def bulk_create(self, snapshots: List[dict]) -> List[PriceSnapshot]:
        objs = [PriceSnapshot(**s) for s in snapshots]
        self.db.add_all(objs)
        await self.db.flush()
        return objs

    async def get_latest(self, symbols: List[str]) -> dict:
        """Return {symbol: PriceSnapshot} for the latest snapshot of each symbol."""
        from sqlalchemy import text
        upper_symbols = [s.upper() for s in symbols]
        # Use a correlated subquery approach that's more SQLAlchemy-friendly
        sub = (
            select(func.max(PriceSnapshot.snapshot_at).label("max_at"))
            .where(PriceSnapshot.symbol == PriceSnapshot.symbol)
            .correlate(PriceSnapshot)
            .scalar_subquery()
        )
        # Simpler: fetch all snapshots for the symbols, pick latest per symbol in Python
        q = (
            select(PriceSnapshot)
            .where(PriceSnapshot.symbol.in_(upper_symbols))
            .order_by(PriceSnapshot.symbol, PriceSnapshot.snapshot_at.desc())
        )
        rows = list((await self.db.execute(q)).scalars().all())
        # Deduplicate: keep latest per symbol
        result: dict = {}
        for row in rows:
            if row.symbol not in result:
                result[row.symbol] = row
        return result

    async def get_history(
        self, symbol: str, from_dt: Optional[datetime] = None, limit: int = 100
    ) -> List[PriceSnapshot]:
        q = select(PriceSnapshot).where(PriceSnapshot.symbol == symbol.upper())
        if from_dt:
            q = q.where(PriceSnapshot.snapshot_at >= from_dt)
        q = q.order_by(PriceSnapshot.snapshot_at.desc()).limit(limit)
        return list((await self.db.execute(q)).scalars().all())


class WatchlistRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> List[WatchlistItem]:
        """Return all watchlist items for the tenant (shared across all users)."""
        q = select(WatchlistItem).where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.is_deleted == False,
        ).order_by(WatchlistItem.sort_order, WatchlistItem.symbol)
        return list((await self.db.execute(q)).scalars().all())

    # Keep old method as alias for backward compat
    async def get_by_user(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> List[WatchlistItem]:
        return await self.get_by_tenant(tenant_id)

    async def add(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> WatchlistItem:
        obj = WatchlistItem(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_item(self, item_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[WatchlistItem]:
        """Find watchlist item by ID within the tenant (not restricted to one user)."""
        q = select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def remove(self, item: WatchlistItem) -> None:
        item.is_deleted = True
        await self.db.flush()
