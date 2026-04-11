import uuid
from sqlalchemy import String, Text, UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantScopedModel


class Permission(BaseModel):
    """System-level permission definitions (module + action pairs).
    These are seeded by the system, not created by users.
    """
    __tablename__ = "permissions"

    module: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", lazy="noload"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.module}.{self.action}>"


class RolePermission(BaseModel):
    """Maps a role to a permission within a tenant."""
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions", lazy="noload")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions", lazy="noload")
