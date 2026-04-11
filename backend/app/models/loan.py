"""Loan and LoanInstallment models — borrowed fund management."""
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


class LoanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID_OFF = "PAID_OFF"
    RESTRUCTURED = "RESTRUCTURED"
    DEFAULTED = "DEFAULTED"
    CANCELLED = "CANCELLED"


class InstallmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    WAIVED = "WAIVED"


class Loan(TenantScopedModel):
    """Loan/credit facility tracking with full repayment schedule support."""
    __tablename__ = "loans"

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[LoanStatus] = mapped_column(
        String(50), nullable=False, default=LoanStatus.ACTIVE
    )

    lender_name: Mapped[str] = mapped_column(String(300), nullable=False)
    loan_purpose: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Financials
    principal: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    disbursed_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6), nullable=False, default=Decimal("0")
    )
    total_interest: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    fees: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")

    # Schedule
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    installment_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Repayment tracking
    total_paid: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    remaining_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )

    # Linked account (settlement account)
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    # Category (used for all installment transactions)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    account: Mapped[Optional["Account"]] = relationship("Account", lazy="noload")
    installments: Mapped[List["LoanInstallment"]] = relationship(
        "LoanInstallment", back_populates="loan", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Loan {self.lender_name} {self.principal} {self.currency} [{self.status}]>"


class LoanInstallment(BaseModel):
    """Individual repayment installment for a loan."""
    __tablename__ = "loan_installments"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False
    )
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    interest_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[InstallmentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=InstallmentStatus.PENDING,
    )
    linked_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    loan: Mapped["Loan"] = relationship("Loan", back_populates="installments", lazy="noload")

    def __repr__(self) -> str:
        return f"<LoanInstallment #{self.installment_number} {self.total_amount} [{self.status}]>"
