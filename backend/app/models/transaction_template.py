"""Transaction template model — reusable transaction presets."""
import uuid
from typing import Optional
from sqlalchemy import String, Text, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class TransactionTemplate(TenantScopedModel):
    """Saved transaction preset for quick re-use."""
    __tablename__ = "transaction_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")

    source_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    target_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
