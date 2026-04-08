"""OCR draft model — AI extraction output, ALWAYS a draft until human confirms."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Numeric, Boolean, Date, DateTime,
    UUID, ForeignKey, Enum as SAEnum, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel


class OcrDraftStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class OcrDraft(TenantScopedModel):
    """
    AI/OCR extraction result. THIS IS ALWAYS A DRAFT.
    Rule: Never create a real transaction automatically from this record.
    A human must review and explicitly accept before a real transaction is posted.
    """
    __tablename__ = "ocr_drafts"
    __table_args__ = (
        Index("ix_ocr_drafts_tenant", "tenant_id"),
        Index("ix_ocr_drafts_status", "status"),
    )

    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(OcrDraftStatus, native_enum=False, length=50),
        nullable=False, default=OcrDraftStatus.PENDING
    )

    # AI-suggested fields — all optional, all unconfirmed
    suggested_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=4), nullable=True)
    suggested_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    suggested_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    suggested_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    suggested_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    suggested_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    suggested_transaction_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Raw extraction data and confidence
    raw_extraction: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=4, scale=3), nullable=True)

    # Human review
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Result: only filled when ACCEPTED
    accepted_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<OcrDraft {self.status} amount={self.suggested_amount} [{self.id}]>"
