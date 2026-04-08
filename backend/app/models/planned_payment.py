"""PlannedPayment model — future expected income/expense events."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, Integer,
    UUID, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel


class PlannedPaymentType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class PlannedPaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    PARTIALLY_PAID = "PARTIALLY_PAID"


class RecurrenceRule(str, enum.Enum):
    NONE = "NONE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class PlannedPayment(TenantScopedModel):
    """
    Planned future payment. NOT a real transaction until executed/converted.
    Supports recurring and installment-based schedules.
    """
    __tablename__ = "planned_payments"

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    payment_type: Mapped[PlannedPaymentType] = mapped_column(
        String(50), nullable=False
    )
    status: Mapped[PlannedPaymentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=PlannedPaymentStatus.PENDING,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False, default=Decimal("0")
    )

    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reminder_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Recurrence
    recurrence_rule: Mapped[RecurrenceRule] = mapped_column(
        String(50),
        nullable=False,
        default=RecurrenceRule.NONE,
    )
    recurrence_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    recurrence_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Installment
    total_installments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_installment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_planned_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planned_payments.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Linked transaction (when converted/executed)
    linked_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Credit card purchase link (when created from a CC purchase installment)
    credit_card_purchase_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_card_purchases.id", ondelete="SET NULL"), nullable=True
    )

    # Loan link (when created from a loan installment)
    loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    account: Mapped[Optional["Account"]] = relationship("Account", lazy="noload")
    category: Mapped[Optional["Category"]] = relationship("Category", lazy="noload")

    def __repr__(self) -> str:
        return f"<PlannedPayment {self.title} {self.amount} [{self.status}]>"
