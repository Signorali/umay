"""DeleteRequest model — tracks user-initiated deletion requests pending admin approval."""
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, UUID, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel

# Tables that can have delete requests raised against them
ALLOWED_TARGET_TABLES = {
    "transactions",
    "categories",
    "accounts",
    "planned_payments",
    "loans",
    "credit_cards",
    "assets",
    "documents",
}


class DeleteRequest(TenantScopedModel):
    """A request by a non-admin user to delete a record. Requires admin approval."""
    __tablename__ = "delete_requests"
    __table_args__ = (
        Index("ix_delete_requests_tenant_status", "tenant_id", "status"),
        Index("ix_delete_requests_target", "target_table", "target_id"),
        Index("ix_delete_requests_requester", "requested_by_user_id"),
    )

    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_label: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow: pending → approved | rejected
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    requested_by: Mapped["User"] = relationship(
        "User", foreign_keys=[requested_by_user_id], lazy="noload"
    )
    reviewed_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by_user_id], lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<DeleteRequest {self.target_table}/{self.target_id} [{self.status}]>"
