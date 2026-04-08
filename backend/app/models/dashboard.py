"""Dashboard widget configuration model."""
import uuid
from typing import Optional
from sqlalchemy import (
    String, Boolean, Integer, UUID, ForeignKey, Enum as SAEnum, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import BaseModel


class WidgetType(str, enum.Enum):
    ACCOUNT_SUMMARY = "ACCOUNT_SUMMARY"
    INCOME_EXPENSE = "INCOME_EXPENSE"
    PLANNED_PAYMENTS = "PLANNED_PAYMENTS"
    LOAN_SUMMARY = "LOAN_SUMMARY"
    CARD_DUE = "CARD_DUE"
    PORTFOLIO_TOTAL = "PORTFOLIO_TOTAL"
    MARKET_SYMBOLS = "MARKET_SYMBOLS"
    RECENT_TRANSACTIONS = "RECENT_TRANSACTIONS"
    ASSET_VALUE = "ASSET_VALUE"
    CASH_FLOW = "CASH_FLOW"
    CATEGORY_BREAKDOWN = "CATEGORY_BREAKDOWN"
    CUSTOM = "CUSTOM"


class DashboardWidget(BaseModel):
    """
    User-level configurable dashboard widget.
    Each widget type maps to a different data query in DashboardService.
    """
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        Index("ix_dashboard_widgets_user", "user_id"),
        Index("ix_dashboard_widgets_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    widget_type: Mapped[WidgetType] = mapped_column(
        String(50), nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    col_span: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    row_span: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    user: Mapped["User"] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<DashboardWidget {self.widget_type} pos={self.position} user={self.user_id}>"
