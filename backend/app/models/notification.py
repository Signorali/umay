"""Notification model — in-app notification store."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, DateTime, UUID,
    ForeignKey, Enum as SAEnum, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel


class NotificationType(str, enum.Enum):
    # Financial alerts
    PAYMENT_DUE      = "PAYMENT_DUE"        # Planned payment approaching
    PAYMENT_OVERDUE  = "PAYMENT_OVERDUE"     # Planned payment past due
    LOAN_DUE         = "LOAN_DUE"            # Loan installment due
    CARD_DUE         = "CARD_DUE"            # Credit card statement due
    BALANCE_LOW      = "BALANCE_LOW"         # Account balance below threshold
    # Operations
    IMPORT_DONE      = "IMPORT_DONE"         # CSV import completed
    BACKUP_DONE      = "BACKUP_DONE"         # Backup completed/failed
    OCR_READY        = "OCR_READY"           # OCR draft ready for review
    # System
    PERIOD_LOCKED    = "PERIOD_LOCKED"       # An accounting period was locked
    SYSTEM_UPDATE    = "SYSTEM_UPDATE"       # System announcement
    CUSTOM           = "CUSTOM"              # Admin custom message


class NotificationPriority(str, enum.Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"
    URGENT = "URGENT"


class Notification(BaseModel):
    """
    In-app notification record.
    Append-only: never deleted (only marked read).
    One notification per (user, event) — deduplication via idempotency_key.
    """
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_tenant", "tenant_id"),
        Index("ix_notifications_type", "notification_type"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NotificationPriority.MEDIUM
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Action link (e.g., /planned-payments to show the related record)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Extra context (e.g., {"amount": "1500", "due_date": "2025-02-01"})
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Idempotency: system jobs use this to avoid duplicate notifications
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    user: Mapped["User"] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<Notification [{self.notification_type}] '{self.title}' read={self.is_read}>"
