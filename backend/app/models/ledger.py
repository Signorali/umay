"""LedgerEntry model — double-entry accounting engine records."""
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Numeric, DateTime, UUID, ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel


class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(BaseModel):
    """
    Double-entry ledger record.
    
    Every confirmed transaction must produce balanced ledger entries:
    sum(DEBIT amounts) == sum(CREDIT amounts) per transaction.
    
    This table is append-only. Never update or delete ledger entries.
    Use reversal transactions to correct errors.
    """
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_transaction", "transaction_id"),
        Index("ix_ledger_account_posted", "account_id", "posted_at"),
    )

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(
        String(50), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="ledger_entries", lazy="noload"
    )
    account: Mapped["Account"] = relationship("Account", lazy="noload")

    def __repr__(self) -> str:
        return f"<LedgerEntry {self.entry_type} {self.amount} {self.currency} @ account={self.account_id}>"
