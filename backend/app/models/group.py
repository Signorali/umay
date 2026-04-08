import uuid
from typing import Optional
from sqlalchemy import String, Text, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantScopedModel


class Group(TenantScopedModel):
    """Groups allow data isolation within a tenant (branch, department, family unit, etc.)."""
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="groups", lazy="noload")
    user_groups: Mapped[list["UserGroup"]] = relationship("UserGroup", back_populates="group", lazy="noload")

    def __repr__(self) -> str:
        return f"<Group {self.name}>"
