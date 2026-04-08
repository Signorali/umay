import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import Text, Boolean, DateTime, Integer, ForeignKey, UUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class TenantLicense(BaseModel):
    """
    Stores the active license for a tenant.
    The license_key contains the full signed UMAY.1.* token.
    Verification is done cryptographically; this table is the source of truth
    for the current key string and caches the decoded metadata for quick reads.
    """
    __tablename__ = "tenant_licenses"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # The full signed license key (UMAY.1.payload.signature)
    license_key: Mapped[str] = mapped_column(Text, nullable=False)

    # Decoded metadata — cached for display, always re-verified via crypto
    license_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="trial")
    issued_to: Mapped[str] = mapped_column(String(255), nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    features_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Activation state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Last successful verification timestamp (for audit/debug)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<TenantLicense tenant={self.tenant_id} plan={self.plan}>"
