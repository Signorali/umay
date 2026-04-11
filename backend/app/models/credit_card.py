"""CreditCard, CreditCardPurchase, CreditCardStatement, CreditCardStatementLine models."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, Integer,
    UUID, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel, BaseModel


class CardStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class StatementStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    OVERDUE = "OVERDUE"


class PurchaseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class StatementLineType(str, enum.Enum):
    INSTALLMENT = "INSTALLMENT"
    NEW_SPENDING = "NEW_SPENDING"
    REFUND = "REFUND"


class CreditCard(TenantScopedModel):
    """Credit card definition with billing cycle tracking."""
    __tablename__ = "credit_cards"

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[CardStatus] = mapped_column(
        String(50), nullable=False, default=CardStatus.ACTIVE
    )

    card_name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    card_type: Mapped[str] = mapped_column(String(50), nullable=False, default="CREDIT")
    network: Mapped[str] = mapped_column(String(50), nullable=False, default="VISA")
    last_four_digits: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)

    # Limit & currency
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    current_debt: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")

    # Billing cycle
    statement_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-31
    due_day: Mapped[int] = mapped_column(Integer, nullable=False)        # 1-31

    # Linked accounts
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True,
        comment="Credit card liability account"
    )
    payment_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True,
        comment="Cash/bank account used to pay card bill"
    )

    expiry_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expiry_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Encrypted sensitive fields
    card_number_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cvv_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[account_id], lazy="noload"
    )
    payment_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[payment_account_id], lazy="noload"
    )
    statements: Mapped[List["CreditCardStatement"]] = relationship(
        "CreditCardStatement", back_populates="card", lazy="noload", cascade="all, delete-orphan"
    )
    purchases: Mapped[List["CreditCardPurchase"]] = relationship(
        "CreditCardPurchase", back_populates="card", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CreditCard {self.card_name} @ {self.bank_name} [{self.status}]>"


class CreditCardPurchase(TenantScopedModel):
    """Installment or single-payment purchase on a credit card."""
    __tablename__ = "credit_card_purchases"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    installment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)

    remaining_installments: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[PurchaseStatus] = mapped_column(
        String(50),
        nullable=False, default=PurchaseStatus.ACTIVE
    )

    # Relationships
    card: Mapped["CreditCard"] = relationship("CreditCard", back_populates="purchases", lazy="noload")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<CreditCardPurchase {self.description} {self.total_amount} [{self.status}]>"


class CreditCardStatement(BaseModel):
    """Monthly billing statement for a credit card."""
    __tablename__ = "credit_card_statements"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[StatementStatus] = mapped_column(
        String(50),
        nullable=False,
        default=StatementStatus.OPEN,
    )

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    statement_closing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_spending: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    minimum_payment: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )

    # Payment tracking
    payment_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # New spending calculated during generation
    theoretical_available: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    real_available: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    new_spending: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )

    card: Mapped["CreditCard"] = relationship("CreditCard", back_populates="statements", lazy="noload")
    lines: Mapped[List["CreditCardStatementLine"]] = relationship(
        "CreditCardStatementLine", back_populates="statement", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CreditCardStatement {self.period_start} → {self.period_end} [{self.status}]>"


class CreditCardStatementLine(BaseModel):
    """Individual line item within a credit card statement."""
    __tablename__ = "credit_card_statement_lines"

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_card_statements.id", ondelete="CASCADE"), nullable=False
    )
    purchase_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_card_purchases.id", ondelete="SET NULL"), nullable=True
    )
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    line_type: Mapped[StatementLineType] = mapped_column(
        String(50), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)

    installment_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_installments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    statement: Mapped["CreditCardStatement"] = relationship(
        "CreditCardStatement", back_populates="lines", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<CreditCardStatementLine {self.line_type} {self.description} {self.amount}>"
