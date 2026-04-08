"""Credit card purchase template — reusable purchase presets."""
import uuid
from typing import Optional
from sqlalchemy import String, Integer, UUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class CcPurchaseTemplate(TenantScopedModel):
    """Saved credit card purchase preset for quick re-use."""
    __tablename__ = "cc_purchase_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    installment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="TRY")
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
