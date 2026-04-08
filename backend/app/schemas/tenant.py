import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator
import re


class TenantCreate(BaseModel):
    name: str
    slug: str
    contact_email: Optional[str] = None
    base_currency: str = "TRY"
    timezone: str = "Europe/Istanbul"
    locale: str = "tr-TR"

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    base_currency: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    contact_email: Optional[str]
    base_currency: str
    timezone: str
    locale: str
    is_setup_complete: bool
    created_at: datetime

    model_config = {"from_attributes": True}
