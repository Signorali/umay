"""Document model — file storage with polymorphic financial linkage."""
import uuid
from typing import Optional
from sqlalchemy import (
    String, Text, Boolean, BigInteger, UUID,
    ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel


class DocumentType(str, enum.Enum):
    RECEIPT = "RECEIPT"
    INVOICE = "INVOICE"
    VOUCHER = "VOUCHER"
    CONTRACT = "CONTRACT"
    STATEMENT = "STATEMENT"
    PHOTO = "PHOTO"
    REPORT = "REPORT"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    STORED = "STORED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class Document(TenantScopedModel):
    """
    Represents an uploaded file linked to financial operations.
    File content is stored in the filesystem (STORAGE_PATH).
    This table stores only metadata and linkage.
    """
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_tenant", "tenant_id"),
        Index("ix_documents_tx", "linked_transaction_id"),
    )

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(
        SAEnum(DocumentType, native_enum=False, length=50),
        nullable=False, default=DocumentType.OTHER
    )
    status: Mapped[str] = mapped_column(
        SAEnum(DocumentStatus, native_enum=False, length=50),
        nullable=False, default=DocumentStatus.PENDING
    )

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Financial linkage (polymorphic)
    linked_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    linked_planned_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planned_payments.id", ondelete="SET NULL"), nullable=True
    )
    linked_loan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True
    )
    linked_credit_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True
    )
    linked_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    # OCR
    ocr_extracted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_draft_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Description
    title: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<Document {self.original_filename} [{self.document_type}/{self.status}]>"
