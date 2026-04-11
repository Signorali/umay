"""Investment repositories — portfolios, transactions, positions."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment import Portfolio, InvestmentTransaction, PortfolioPosition, MarketPrice
from app.models.institution import InstitutionGroupLink


class PortfolioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Portfolio:
        obj = Portfolio(tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Portfolio]:
        q = select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.tenant_id == tenant_id,
            Portfolio.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        group_id: Optional[uuid.UUID] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Portfolio]:
        from sqlalchemy import or_
        q = select(Portfolio).where(Portfolio.tenant_id == tenant_id, Portfolio.is_deleted == False)
        if group_ids:
            # Match portfolios either by direct group_id OR via the institution's group links
            inst_linked = (
                select(InstitutionGroupLink.institution_id)
                .where(InstitutionGroupLink.group_id.in_(group_ids))
            )
            q = q.where(
                Portfolio.group_id.in_(group_ids) |
                Portfolio.institution_id.in_(inst_linked)
            )
        elif group_id:
            q = q.where(Portfolio.group_id == group_id)
        if active_only:
            q = q.where(Portfolio.is_active == True)
        q = q.order_by(Portfolio.name).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def update(self, portfolio: Portfolio, data: dict) -> Portfolio:
        for k, v in data.items():
            setattr(portfolio, k, v)
        await self.db.flush()
        await self.db.refresh(portfolio)
        return portfolio

    async def soft_delete(self, portfolio: Portfolio) -> None:
        portfolio.is_deleted = True
        await self.db.flush()


class InvestmentTransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, portfolio_id: uuid.UUID, data: dict) -> InvestmentTransaction:
        obj = InvestmentTransaction(portfolio_id=portfolio_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, tx_id: uuid.UUID, portfolio_id: uuid.UUID) -> Optional[InvestmentTransaction]:
        q = select(InvestmentTransaction).where(
            InvestmentTransaction.id == tx_id,
            InvestmentTransaction.portfolio_id == portfolio_id,
            InvestmentTransaction.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_portfolio(
        self,
        portfolio_id: uuid.UUID,
        symbol: Optional[str] = None,
        transaction_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InvestmentTransaction]:
        q = select(InvestmentTransaction).where(
            InvestmentTransaction.portfolio_id == portfolio_id,
            InvestmentTransaction.is_deleted == False,
        )
        if symbol:
            q = q.where(InvestmentTransaction.symbol == symbol.upper())
        if transaction_type:
            q = q.where(InvestmentTransaction.transaction_type == transaction_type)
        if date_from:
            q = q.where(InvestmentTransaction.transaction_date >= date_from)
        if date_to:
            q = q.where(InvestmentTransaction.transaction_date <= date_to)
        q = q.order_by(InvestmentTransaction.transaction_date.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def get_symbol_history(self, portfolio_id: uuid.UUID, symbol: str) -> List[InvestmentTransaction]:
        """All BUY/SELL for a symbol, ordered chronologically (for FIFO calc)."""
        q = select(InvestmentTransaction).where(
            InvestmentTransaction.portfolio_id == portfolio_id,
            InvestmentTransaction.symbol == symbol.upper(),
            InvestmentTransaction.transaction_type.in_(["BUY", "SELL"]),
            InvestmentTransaction.is_deleted == False,
        ).order_by(InvestmentTransaction.transaction_date)
        return list((await self.db.execute(q)).scalars().all())


class PortfolioPositionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, portfolio_id: uuid.UUID, symbol: str) -> PortfolioPosition:
        # Include soft-deleted rows to avoid unique constraint violations on re-use
        q = select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.symbol == symbol.upper(),
        )
        pos = (await self.db.execute(q)).scalar_one_or_none()
        if not pos:
            pos = PortfolioPosition(portfolio_id=portfolio_id, symbol=symbol.upper())
            self.db.add(pos)
            await self.db.flush()
            await self.db.refresh(pos)
        else:
            # Resurrect if previously deleted
            pos.is_deleted = False
            await self.db.flush()
        return pos

    async def list_by_portfolio(self, portfolio_id: uuid.UUID) -> List[PortfolioPosition]:
        q = select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.quantity > 0,
            PortfolioPosition.is_deleted == False,
        ).order_by(PortfolioPosition.symbol)
        return list((await self.db.execute(q)).scalars().all())

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> List[PortfolioPosition]:
        from app.models.investment import Portfolio
        q = select(PortfolioPosition).join(
            Portfolio, Portfolio.id == PortfolioPosition.portfolio_id
        ).where(
            Portfolio.tenant_id == tenant_id,
            PortfolioPosition.quantity > 0,
            PortfolioPosition.is_deleted == False,
        ).order_by(PortfolioPosition.symbol)
        return list((await self.db.execute(q)).scalars().all())

    async def update(self, position: PortfolioPosition, data: dict) -> PortfolioPosition:
        for k, v in data.items():
            setattr(position, k, v)
        await self.db.flush()
        await self.db.refresh(position)
        return position


class MarketPriceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, tenant_id: uuid.UUID, symbol: str) -> MarketPrice:
        q = select(MarketPrice).where(
            MarketPrice.tenant_id == tenant_id,
            MarketPrice.symbol == symbol.upper(),
        )
        obj = (await self.db.execute(q)).scalar_one_or_none()
        if not obj:
            obj = MarketPrice(tenant_id=tenant_id, symbol=symbol.upper())
            self.db.add(obj)
            await self.db.flush()
            await self.db.refresh(obj)
        return obj

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> List[MarketPrice]:
        q = select(MarketPrice).where(
            MarketPrice.tenant_id == tenant_id,
            MarketPrice.is_deleted == False
        ).order_by(MarketPrice.symbol)
        return list((await self.db.execute(q)).scalars().all())

    async def delete_by_symbol(self, tenant_id: uuid.UUID, symbol: str) -> None:
        q = select(MarketPrice).where(
            MarketPrice.tenant_id == tenant_id,
            MarketPrice.symbol == symbol.upper(),
        )
        obj = (await self.db.execute(q)).scalar_one_or_none()
        if obj:
            obj.is_deleted = True
            await self.db.flush()
