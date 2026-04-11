"""Market data models — providers, price snapshots, and watchlists."""
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Numeric, Boolean, DateTime, Integer,
    UUID, ForeignKey, Enum as SAEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel, TenantScopedModel


class ProviderType(str, enum.Enum):
    FREE_API = "FREE_API"
    PAID_API = "PAID_API"
    MANUAL = "MANUAL"
    INTERNAL = "INTERNAL"


class MarketProvider(BaseModel):
    """External or internal market data provider definition."""
    __tablename__ = "market_providers"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    provider_type: Mapped[str] = mapped_column(
        SAEnum(ProviderType, native_enum=False, length=50),
        nullable=False, default=ProviderType.FREE_API
    )
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    api_key_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    supported_symbols: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<MarketProvider {self.name} ({self.provider_type})>"


class PriceSnapshot(BaseModel):
    """
    Append-only price snapshot per symbol per provider.
    Never updated — add new snapshot when price changes.
    """
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("ix_price_snapshots_symbol_time", "symbol", "snapshot_at"),
    )

    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("market_providers.id", ondelete="SET NULL"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    change_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4), nullable=True)
    trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_realtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    provider: Mapped[Optional["MarketProvider"]] = relationship("MarketProvider", lazy="noload")

    def __repr__(self) -> str:
        return f"<PriceSnapshot {self.symbol}={self.price} ({self.trend} {self.change_percent}%) @ {self.snapshot_at}>"


class WatchlistItem(TenantScopedModel):
    """User/group watchlist item linking to a market symbol."""
    __tablename__ = "watchlist_items"
    __table_args__ = (
        Index("ix_watchlist_tenant", "tenant_id"),
        UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    instrument_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="google_finance")
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # formula-based custom symbols

    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<WatchlistItem {self.symbol} ({self.label})>"
