"""Market data Pydantic schemas."""
import uuid
from typing import Optional, List
from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    label: Optional[str] = None
    instrument_type: Optional[str] = None
    sort_order: int = 0
    source: str = Field(default="google_finance")
    formula: Optional[str] = None  # e.g. "USDTRY * GOLD / 31.1"


class WatchlistItemResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    label: Optional[str]
    instrument_type: Optional[str]
    sort_order: int
    source: str = "google_finance"
    price: Optional[float] = None
    currency: Optional[str] = None
    snapshot_at: Optional[str] = None

    model_config = {"from_attributes": True}


class PriceResponse(BaseModel):
    symbol: str
    price: float
    currency: str
    snapshot_at: str
    is_realtime: bool


class PricesResponse(BaseModel):
    prices: dict


class MarketProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider_type: str = "FREE_API"
    base_url: Optional[str] = None
    api_key_ref: Optional[str] = None
    supported_symbols: Optional[str] = None
    priority: int = 0
    notes: Optional[str] = None


class MarketProviderResponse(BaseModel):
    id: uuid.UUID
    name: str
    provider_type: str
    base_url: Optional[str]
    is_active: bool
    priority: int

    model_config = {"from_attributes": True}
