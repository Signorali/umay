"""Demo session model."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, UUID, ForeignKey, JSON, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DemoSession(BaseModel):
    """
    Tracks active demo data seeding for a tenant.
    All seeded records are tracked by ID for safe removal.
    """
    __tablename__ = "demo_sessions"
    __table_args__ = (
        Index("ix_demo_sessions_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    seeded_modules: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seed_record_ids: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<DemoSession tenant={self.tenant_id} active={self.is_active}>"
