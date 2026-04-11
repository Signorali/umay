from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LicenseActivateRequest(BaseModel):
    """Request body for activating a license key."""
    license_key: str = Field(..., description="Full UMAY.1.* signed license key")


class LicenseStatusResponse(BaseModel):
    """Current license status returned to the frontend."""
    is_licensed: bool
    plan: str                          # trial | starter | professional | enterprise
    issued_to: str
    max_users: int
    features: list[str]
    issued_at: Optional[datetime]
    expires_at: Optional[datetime]
    days_until_expiry: Optional[int]   # None = perpetual
    is_expired: bool
    license_id: Optional[str]          # UUID, shown in admin UI


class LicenseActivateResponse(BaseModel):
    """Response after successful license activation."""
    success: bool
    message: str
    status: LicenseStatusResponse
