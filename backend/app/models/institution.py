"""Institution, CommissionRule, and TaxRule models."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, Integer, UUID, ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel, BaseModel


class InstitutionType(str, enum.Enum):
    BANK = "BANK"
    BROKERAGE = "BROKERAGE"
    EXCHANGE = "EXCHANGE"
    INSURANCE = "INSURANCE"
    OTHER = "OTHER"


class CommissionBasis(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"
    PER_UNIT = "PER_UNIT"


class TaxRuleType(str, enum.Enum):
    WITHHOLDING = "WITHHOLDING"
    CAPITAL_GAINS = "CAPITAL_GAINS"
    VAT = "VAT"
    STAMP_DUTY = "STAMP_DUTY"
    OTHER = "OTHER"


class Institution(TenantScopedModel):
    """Financial institution definition (bank, broker, exchange, etc.)."""
    __tablename__ = "institutions"
    __table_args__ = (
        Index("ix_institutions_tenant_id", "tenant_id"),
    )

    institution_type: Mapped[str] = mapped_column(
        SAEnum(InstitutionType, native_enum=False, length=50), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    swift_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Representative info
    rep_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rep_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rep_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    commission_rules: Mapped[List["CommissionRule"]] = relationship(
        "CommissionRule", back_populates="institution", lazy="noload", cascade="all, delete-orphan"
    )
    tax_rules: Mapped[List["TaxRule"]] = relationship(
        "TaxRule", back_populates="institution", lazy="noload", cascade="all, delete-orphan"
    )
    group_links: Mapped[List["InstitutionGroupLink"]] = relationship(
        "InstitutionGroupLink", cascade="all, delete-orphan", lazy="noload",
        foreign_keys="InstitutionGroupLink.institution_id"
    )

    def __repr__(self) -> str:
        return f"<Institution {self.name} ({self.institution_type})>"


class InstitutionGroupLink(BaseModel):
    """Many-to-many: one institution → many groups."""
    __tablename__ = "institution_group_links"
    __table_args__ = (
        Index("ix_institution_group_links_institution_id", "institution_id"),
        Index("ix_institution_group_links_group_id", "group_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )


class CommissionRule(BaseModel):
    """Commission rule for a specific instrument type at an institution."""
    __tablename__ = "commission_rules"
    __table_args__ = (
        Index("ix_commission_rules_institution_id", "institution_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    instrument_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    basis: Mapped[str] = mapped_column(
        SAEnum(CommissionBasis, native_enum=False, length=50),
        nullable=False, default=CommissionBasis.PERCENTAGE
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=6), nullable=False, default=Decimal("0"))
    min_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    max_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    institution: Mapped["Institution"] = relationship("Institution", back_populates="commission_rules", lazy="noload")


class TaxRule(BaseModel):
    """Tax rule for a specific instrument/event type at an institution."""
    __tablename__ = "tax_rules"
    __table_args__ = (
        Index("ix_tax_rules_institution_id", "institution_id"),
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(
        SAEnum(TaxRuleType, native_enum=False, length=50), nullable=False
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=6), nullable=False, default=Decimal("0"))
    instrument_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    institution: Mapped["Institution"] = relationship("Institution", back_populates="tax_rules", lazy="noload")
