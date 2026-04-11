"""Period lock schemas — request/response contracts for accounting period management."""
from typing import List

from pydantic import BaseModel, Field


class PeriodLockOut(BaseModel):
    """Response with all currently locked periods."""
    locked_periods: List[str]  # ["2025-01", "2025-02", ...]
    total_locked: int

    model_config = {"from_attributes": True}


class PeriodStatusOut(BaseModel):
    """Status of a specific period (year + month)."""
    year: int
    month: int
    period: str  # "YYYY-MM"
    is_locked: bool


class PeriodActionIn(BaseModel):
    """Lock or unlock a specific accounting period."""
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
