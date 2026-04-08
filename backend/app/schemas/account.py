"""Account schemas."""
import uuid
from decimal import Decimal
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.account import AccountType


def _to_title_case(text: str) -> str:
    """Convert text to Title Case."""
    if not text:
        return text
    return ' '.join(word.capitalize() for word in text.split())


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    account_type: AccountType
    currency: str = Field(default="TRY", max_length=10)
    opening_balance: Decimal = Field(default=Decimal("0"))
    group_id: Optional[uuid.UUID] = None
    institution_name: Optional[str] = None
    iban: Optional[str] = None
    account_number: Optional[str] = None
    description: Optional[str] = None
    include_in_total: bool = True
    allow_negative_balance: bool = False

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    institution_name: Optional[str] = None
    iban: Optional[str] = None
    account_number: Optional[str] = None
    description: Optional[str] = None
    group_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    include_in_total: Optional[bool] = None
    allow_negative_balance: Optional[bool] = None

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class AccountResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    group_name: Optional[str] = None
    group_names: List[str] = []
    institution_id: Optional[uuid.UUID]
    name: str
    account_type: AccountType
    currency: str
    opening_balance: Decimal
    current_balance: Decimal
    institution_name: Optional[str]
    iban: Optional[str]
    account_number: Optional[str]
    description: Optional[str]
    is_active: bool
    include_in_total: bool
    allow_negative_balance: bool
    created_at: datetime
    is_own_group: bool = True  # False when account belongs to a group the user is not a member of

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
    total: int
