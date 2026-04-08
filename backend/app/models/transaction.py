"""Transaction and LedgerEntry models — the heart of financial recording."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, DateTime,
    UUID, ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel, BaseModel


class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REVERSED = "REVERSED"


class Transaction(TenantScopedModel):
    """
    Main financial data entry. Every confirmed transaction must produce ledger entries.
    Supports income, expense, and transfer flows.
    
    Rule: No direct balance mutation — all balance changes via LedgerEntry posting.
    """
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_tx_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_tx_group_date", "group_id", "transaction_date"),
    )

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        String(50), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=TransactionStatus.DRAFT,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")

    # Accounts
    source_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )
    target_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )

    # Classification
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Dates
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Content
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Ownership — who created this transaction (for delete permission checks)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Reversal linkage
    reversed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    reversal_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    group: Mapped[Optional["Group"]] = relationship("Group", lazy="noload")
    source_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[source_account_id], lazy="noload"
    )
    target_account: Mapped[Optional["Account"]] = relationship(
        "Account", foreign_keys=[target_account_id], lazy="noload"
    )
    category: Mapped[Optional["Category"]] = relationship("Category", lazy="noload")
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(
        "LedgerEntry", back_populates="transaction", lazy="noload"
    )
    tags: Mapped[List["TransactionTag"]] = relationship(
        "TransactionTag", back_populates="transaction", lazy="noload", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} {self.amount} {self.currency} [{self.status}]>"


class TransactionTag(BaseModel):
    """Tags attached to a transaction for flexible labeling."""
    __tablename__ = "transaction_tags"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="tags", lazy="noload")

    def __repr__(self) -> str:
        return f"<TransactionTag {self.tag}>"
