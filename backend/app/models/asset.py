"""Asset models — owned real-world assets and their valuation history."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, UUID, ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel, BaseModel


class AssetType(str, enum.Enum):
    REAL_ESTATE = "REAL_ESTATE"
    VEHICLE = "VEHICLE"
    EQUIPMENT = "EQUIPMENT"
    FINANCIAL = "FINANCIAL"
    LAND = "LAND"
    SECURITY = "SECURITY"
    CRYPTO = "CRYPTO"
    COLLECTIBLE = "COLLECTIBLE"
    OTHER = "OTHER"


class AssetStatus(str, enum.Enum):
    OWNED = "OWNED"
    SOLD = "SOLD"
    LEASED = "LEASED"
    DISPOSED = "DISPOSED"


class Asset(TenantScopedModel):
    """Represents a real-world owned asset with valuation tracking."""
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_tenant_id", "tenant_id"),
        Index("ix_assets_group_id", "group_id"),
        Index("ix_assets_status", "status"),
    )

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    asset_type: Mapped[AssetType] = mapped_column(
        String(50), nullable=False
    )
    status: Mapped[AssetStatus] = mapped_column(
        String(50),
        nullable=False, default=AssetStatus.OWNED
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Purchase
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_value: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    valuation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")

    # Sale / disposal
    sale_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sale_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    sale_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Transaction created when the asset was sold (used to revert on tx deletion)
    sale_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # FX rate to convert asset value to tenant base currency (e.g. 1 USD = 38.5 TRY → fx_rate=38.5)
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8), nullable=False, default=Decimal("1"))

    # Linkage
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    # Account that funds came from when purchasing this asset
    source_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    # Loan used to finance this asset purchase
    loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    group: Mapped[Optional["Group"]] = relationship("Group", lazy="noload")
    account: Mapped[Optional["Account"]] = relationship("Account", foreign_keys=[account_id], lazy="noload")
    valuations: Mapped[List["AssetValuation"]] = relationship(
        "AssetValuation", back_populates="asset", lazy="noload", cascade="all, delete-orphan"
    )
    loan_links: Mapped[List["AssetLoanLink"]] = relationship(
        "AssetLoanLink", cascade="all, delete-orphan", lazy="noload",
        foreign_keys="AssetLoanLink.asset_id"
    )
    account_links: Mapped[List["AssetAccountLink"]] = relationship(
        "AssetAccountLink", cascade="all, delete-orphan", lazy="noload",
        foreign_keys="AssetAccountLink.asset_id"
    )

    @property
    def unrealized_gain(self) -> Decimal:
        return self.current_value - self.purchase_value

    @property
    def realized_gain(self) -> Optional[Decimal]:
        if self.sale_value is not None:
            return self.sale_value - self.purchase_value
        return None

    def __repr__(self) -> str:
        return f"<Asset {self.name} ({self.asset_type}) {self.current_value} {self.currency}>"


class AssetLoanLink(BaseModel):
    """Many-to-many: one asset → many loans."""
    __tablename__ = "asset_loan_links"
    __table_args__ = (
        Index("ix_asset_loan_links_asset_id", "asset_id"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False
    )


class AssetAccountLink(BaseModel):
    """Many-to-many: one asset → many accounts (source or linked)."""
    __tablename__ = "asset_account_links"
    __table_args__ = (
        Index("ix_asset_account_links_asset_id", "asset_id"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(20), nullable=False, default="source")


class AssetValuation(BaseModel):
    """Point-in-time valuation entry for an asset (append-only history)."""
    __tablename__ = "asset_valuations"
    __table_args__ = (
        Index("ix_asset_valuations_asset_id", "asset_id"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="valuations", lazy="noload")

    def __repr__(self) -> str:
        return f"<AssetValuation asset={self.asset_id} {self.value} @ {self.valuation_date}>"
