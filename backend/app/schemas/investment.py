"""Investment Pydantic schemas."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Portfolio
# ------------------------------------------------------------------ #

class PortfolioCreate(BaseModel):
    group_id: Optional[uuid.UUID] = None
    institution_id: Optional[uuid.UUID] = None
    cash_account_id: Optional[uuid.UUID] = None
    name: str = Field(min_length=1, max_length=300)
    currency: str = "TRY"
    notes: Optional[str] = None


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    institution_id: Optional[uuid.UUID] = None
    cash_account_id: Optional[uuid.UUID] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PortfolioResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    institution_id: Optional[uuid.UUID]
    cash_account_id: Optional[uuid.UUID]
    name: str
    currency: str
    is_active: bool
    notes: Optional[str]
    total_value: Optional[Decimal] = Decimal("0")
    unrealized_pnl: Optional[Decimal] = Decimal("0")
    group_names: List[str] = []

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Investment Transaction
# ------------------------------------------------------------------ #

class InvestmentTransactionCreate(BaseModel):
    transaction_type: str
    instrument_type: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    gross_amount: Decimal = Field(ge=0)
    commission: Decimal = Field(ge=0, default=Decimal("0"))
    tax: Decimal = Field(ge=0, default=Decimal("0"))
    net_amount: Decimal
    currency: str = "TRY"
    fx_rate: Optional[Decimal] = Decimal("1")
    transaction_date: date
    settlement_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    linked_transaction_id: Optional[uuid.UUID] = None


class InvestmentTransactionResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    transaction_type: str
    instrument_type: Optional[str]
    symbol: Optional[str]
    description: Optional[str]
    quantity: Optional[Decimal]
    price: Optional[Decimal]
    gross_amount: Decimal
    commission: Decimal
    tax: Decimal
    net_amount: Decimal
    currency: str
    fx_rate: Optional[Decimal]
    transaction_date: date
    settlement_date: Optional[date]
    reference_number: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Portfolio Position
# ------------------------------------------------------------------ #

class PortfolioPositionResponse(BaseModel):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    symbol: str
    instrument_type: Optional[str]
    quantity: Decimal
    avg_cost: Optional[Decimal]
    total_cost: Optional[Decimal]
    current_price: Optional[Decimal]
    current_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    realized_pnl: Decimal
    currency: str
    last_updated: Optional[datetime]

    model_config = {"from_attributes": True}


class UpdatePositionPriceRequest(BaseModel):
    current_price: Decimal = Field(gt=0)


# ------------------------------------------------------------------ #
# Market Prices
# ------------------------------------------------------------------ #

class MarketPriceResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    name: Optional[str]
    price: Decimal
    currency: str
    last_updated: datetime
    source_symbol: Optional[str]

    model_config = {"from_attributes": True}
