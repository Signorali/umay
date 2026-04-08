"""Investment models — portfolios, transactions, positions."""
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, DateTime, UUID,
    ForeignKey, Enum as SAEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel, BaseModel


class InvestmentTransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST_INCOME = "INTEREST_INCOME"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    FEE = "FEE"
    TAX = "TAX"
    BONUS = "BONUS"
    SPLIT = "SPLIT"


class InstrumentType(str, enum.Enum):
    STOCK = "STOCK"
    BOND = "BOND"
    FUND = "FUND"
    ETF = "ETF"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"
    FX = "FX"
    OPTION = "OPTION"
    FUTURES = "FUTURES"
    OTHER = "OTHER"


class Portfolio(TenantScopedModel):
    """Investment portfolio linked to an institution."""
    __tablename__ = "portfolios"
    __table_args__ = (
        Index("ix_portfolios_tenant_id", "tenant_id"),
    )

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True
    )
    cash_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    group: Mapped[Optional["Group"]] = relationship("Group", lazy="noload")
    institution: Mapped[Optional["Institution"]] = relationship("Institution", lazy="noload")
    transactions: Mapped[List["InvestmentTransaction"]] = relationship(
        "InvestmentTransaction", back_populates="portfolio", lazy="noload", cascade="all, delete-orphan"
    )
    positions: Mapped[List["PortfolioPosition"]] = relationship(
        "PortfolioPosition", back_populates="portfolio", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.name} [{self.currency}]>"


class InvestmentTransaction(BaseModel):
    """Single investment transaction: buy, sell, dividend, fee, etc."""
    __tablename__ = "investment_transactions"
    __table_args__ = (
        Index("ix_inv_tx_portfolio", "portfolio_id"),
        Index("ix_inv_tx_date", "portfolio_id", "transaction_date"),
        Index("ix_inv_tx_symbol", "symbol"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(
        SAEnum(InvestmentTransactionType, native_enum=False, length=50),
        nullable=False
    )
    instrument_type: Mapped[Optional[str]] = mapped_column(
        SAEnum(InstrumentType, native_enum=False, length=50), nullable=True
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Amounts
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    fx_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=8), nullable=True, default=Decimal("1"))

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Linkage to main transaction ledger
    linked_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    commission_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="transactions", lazy="noload")

    def __repr__(self) -> str:
        return f"<InvestmentTransaction {self.transaction_type} {self.symbol} {self.net_amount}>"


class PortfolioPosition(BaseModel):
    """Cached current holding for a symbol in a portfolio (recalculated on transactions)."""
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        Index("ix_positions_portfolio", "portfolio_id"),
        UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    instrument_type: Mapped[Optional[str]] = mapped_column(
        SAEnum(InstrumentType, native_enum=False, length=50), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False, default=Decimal("0"))
    avg_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    total_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=8), nullable=True)
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions", lazy="noload")

    def __repr__(self) -> str:
        return f"<PortfolioPosition {self.symbol} qty={self.quantity} @ {self.portfolio_id}>"


class MarketPrice(BaseModel):
    """Global price tracker for symbols, shared across all users but scoped by tenant for privacy if needed."""
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", name="uq_market_price_tenant_symbol"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Google Finance specific identifier (e.g. IST:THYAO)
    source_symbol: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<MarketPrice {self.symbol}: {self.price} {self.currency}>"
