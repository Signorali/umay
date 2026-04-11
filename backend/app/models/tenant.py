from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Tenant(BaseModel):
    """A tenant is a fully isolated data domain (company, family, organization)."""
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Contact / metadata
    contact_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # System settings (JSON stored as text for portability)
    base_currency: Mapped[str] = mapped_column(String(10), default="TRY", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Istanbul", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="tr-TR", nullable=False)

    # Installation state
    is_setup_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Trial — kurulum tarihinden itibaren 30 gün (lisans aktive edilmeden)
    trial_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="noload")
    groups: Mapped[list["Group"]] = relationship("Group", back_populates="tenant", lazy="noload")
    roles: Mapped[list["Role"]] = relationship("Role", back_populates="tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"
