"""Symbol-based peer obligations (borç / alacak)."""
import uuid
import enum
from datetime import date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantScopedModel


class ObligationDirection(str, enum.Enum):
    BORROW = "BORROW"
    LEND   = "LEND"


class ObligationCounterpartyType(str, enum.Enum):
    EXTERNAL = "EXTERNAL"
    USER     = "USER"


class ObligationStatus(str, enum.Enum):
    PENDING   = "PENDING"
    SETTLED   = "SETTLED"
    CANCELLED = "CANCELLED"


class SymbolObligation(TenantScopedModel):
    __tablename__ = "symbol_obligations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str]  = mapped_column(String(50), nullable=False)
    label:  Mapped[str]  = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    price_per_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="TRY", nullable=False)

    # VARCHAR instead of native PG enums — avoids asyncpg type creation issues
    direction: Mapped[str] = mapped_column(String(10), nullable=False)          # BORROW | LEND
    counterparty_type: Mapped[str] = mapped_column(String(10), nullable=False)  # EXTERNAL | USER
    counterparty_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(15), default="PENDING", nullable=False)  # PENDING | SETTLED | CANCELLED
    peer_obligation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("symbol_obligations.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
