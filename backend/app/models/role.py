import uuid
from typing import Optional
from sqlalchemy import String, Text, UUID, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel


class Role(TenantScopedModel):
    """Tenant-scoped role definition. Users are assigned roles."""
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="roles", lazy="noload")
    users: Mapped[list["User"]] = relationship("User", back_populates="role", lazy="noload")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
