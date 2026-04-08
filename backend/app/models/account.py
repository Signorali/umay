"""Account model — financial locations where money lives."""
import uuid
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Text, Numeric, Boolean, UUID, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel


class AccountType(str, enum.Enum):
    CASH = "CASH"
    BANK = "BANK"
    FX = "FX"
    CREDIT = "CREDIT"
    CREDIT_CARD = "CREDIT_CARD"
    INVESTMENT = "INVESTMENT"
    SAVINGS = "SAVINGS"
    OTHER = "OTHER"


class Account(TenantScopedModel):
    """
    Represents every financial location: bank accounts, cash, FX, credit cards,
    investment accounts, etc.
    """
    __tablename__ = "accounts"

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        String(50), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )

    # Institution info
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True
    )
    institution_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_in_total: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_negative_balance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    group: Mapped[Optional["Group"]] = relationship("Group", lazy="noload")

    def __repr__(self) -> str:
        return f"<Account {self.name} ({self.account_type}) {self.currency}>"
