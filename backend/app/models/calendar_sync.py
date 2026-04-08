"""Calendar sync models — reminders, due items, and sync logs."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, DateTime, Integer,
    UUID, ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel, TenantScopedModel


class CalendarItemType(str, enum.Enum):
    PLANNED_PAYMENT = "PLANNED_PAYMENT"
    LOAN_INSTALLMENT = "LOAN_INSTALLMENT"
    CARD_DUE = "CARD_DUE"
    CUSTOM = "CUSTOM"


class CalendarSyncStatus(str, enum.Enum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class CalendarItem(BaseModel):
    """
    Calendar-visible item reflecting a financial obligation.
    Data source is always database — calendar is a reflection layer only.
    """
    __tablename__ = "calendar_items"
    __table_args__ = (
        Index("ix_calendar_items_user", "user_id", "due_date"),
        Index("ix_calendar_items_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(
        SAEnum(CalendarItemType, native_enum=False, length=50), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    reminder_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Source linkage
    linked_planned_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planned_payments.id", ondelete="CASCADE"), nullable=True
    )
    linked_loan_installment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loan_installments.id", ondelete="CASCADE"), nullable=True
    )
    linked_credit_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=True
    )

    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    user: Mapped["User"] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<CalendarItem {self.item_type} '{self.title}' due={self.due_date}>"


class CalendarSyncLog(BaseModel):
    """Audit log for calendar sync operations."""
    __tablename__ = "calendar_sync_logs"
    __table_args__ = (
        Index("ix_cal_sync_logs_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sync_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(CalendarSyncStatus, native_enum=False, length=50),
        nullable=False, default=CalendarSyncStatus.PENDING
    )
    items_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CalendarSyncLog {self.sync_type} [{self.status}] items={self.items_synced}>"
