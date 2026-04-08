"""System meta models — feature flags and maintenance windows."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, UUID, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SystemFlag(BaseModel):
    """
    Key-value store for system-wide flags.
    Examples: maintenance_mode, app_version, last_backup_at
    """
    __tablename__ = "system_flags"

    flag_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    flag_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<SystemFlag {self.flag_key}={self.flag_value}>"


class MaintenanceWindow(BaseModel):
    """Scheduled or unscheduled maintenance windows."""
    __tablename__ = "maintenance_windows"
    __table_args__ = (
        Index("ix_maintenance_windows_active", "is_active", "scheduled_start"),
    )

    label: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<MaintenanceWindow '{self.label}' active={self.is_active}>"
