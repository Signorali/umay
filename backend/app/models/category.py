"""Category model — classify income and expense flows."""
import uuid
from typing import Optional
from sqlalchemy import String, Text, Boolean, UUID, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TenantScopedModel


class CategoryType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class Category(TenantScopedModel):
    """
    Hierarchical categories for transactions.
    Supports parent/child structure and group-aware ownership.
    """
    __tablename__ = "categories"

    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        String(50), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    group: Mapped[Optional["Group"]] = relationship("Group", lazy="noload")
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", remote_side="Category.id", lazy="noload"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent", lazy="noload",
        foreign_keys="Category.parent_id",
    )

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.category_type})>"
