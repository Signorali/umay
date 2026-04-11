"""Asset schemas — request/response models."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class AssetValuationCreate(BaseModel):
    valuation_date: date
    value: Decimal = Field(gt=0)
    currency: str = "TRY"
    source: Optional[str] = None
    notes: Optional[str] = None


class AssetValuationResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    valuation_date: date
    value: Decimal
    currency: str
    source: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    group_id: Optional[uuid.UUID] = None
    asset_type: str
    name: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    purchase_date: date
    purchase_value: Decimal = Field(gt=0)
    current_value: Decimal = Field(gt=0)
    valuation_date: Optional[date] = None
    currency: str = "TRY"
    fx_rate: Decimal = Field(default=Decimal("1"), gt=0)
    loan_ids: List[uuid.UUID] = []
    source_account_ids: List[uuid.UUID] = []
    notes: Optional[str] = None
    # Legacy single-value fields kept for backward compat (ignored if list versions provided)
    account_id: Optional[uuid.UUID] = None
    source_account_id: Optional[uuid.UUID] = None
    loan_id: Optional[uuid.UUID] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_value: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    valuation_date: Optional[date] = None
    currency: Optional[str] = None
    fx_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    group_id: Optional[uuid.UUID] = None
    loan_ids: Optional[List[uuid.UUID]] = None
    source_account_ids: Optional[List[uuid.UUID]] = None


class AssetDisposeRequest(BaseModel):
    sale_date: date
    sale_value: Optional[Decimal] = None
    sale_notes: Optional[str] = None
    is_sold: bool = True
    target_account_id: Optional[uuid.UUID] = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    asset_type: str
    status: str
    name: str
    description: Optional[str]
    purchase_date: date
    purchase_value: Decimal
    current_value: Decimal
    valuation_date: Optional[date]
    currency: str
    fx_rate: Decimal
    sale_date: Optional[date]
    sale_value: Optional[Decimal]
    sale_transaction_id: Optional[uuid.UUID]
    notes: Optional[str]
    loan_ids: List[uuid.UUID] = []
    source_account_ids: List[uuid.UUID] = []

    model_config = {"from_attributes": True}


class AssetPortfolioSummary(BaseModel):
    by_currency: dict
