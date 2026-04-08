import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, UUID, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel, BaseModel


class User(TenantScopedModel):
    """User within a tenant. Always scoped to a tenant."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )

    # Security
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Preferences
    locale: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ui_theme: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'dark' | 'light'
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # MFA / TOTP (cloud.md §14)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mfa_backup_codes: Mapped[Optional[str]] = mapped_column(nullable=True)  # CSV of hashed codes

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users", lazy="noload")
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users", lazy="noload")
    user_groups: Mapped[list["UserGroup"]] = relationship("UserGroup", back_populates="user", lazy="noload")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserGroup(BaseModel):
    """Many-to-many: user membership in groups."""
    __tablename__ = "user_groups"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="user_groups", lazy="noload")
    group: Mapped["Group"] = relationship("Group", back_populates="user_groups", lazy="noload")
