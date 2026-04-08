"""Institution, CommissionRule and TaxRule schemas."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


class CommissionRuleCreate(BaseModel):
    instrument_type: Optional[str] = None
    basis: str = "PERCENTAGE"
    rate: Decimal = Field(ge=0)
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


class CommissionRuleResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    instrument_type: Optional[str]
    basis: str
    rate: Decimal
    min_amount: Optional[Decimal]
    max_amount: Optional[Decimal]
    valid_from: Optional[date]
    valid_to: Optional[date]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class TaxRuleCreate(BaseModel):
    rule_type: str
    rate: Decimal = Field(ge=0)
    instrument_type: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    notes: Optional[str] = None


class TaxRuleResponse(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    rule_type: str
    rate: Decimal
    instrument_type: Optional[str]
    valid_from: Optional[date]
    valid_to: Optional[date]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class InstitutionCreate(BaseModel):
    institution_type: str
    name: str = Field(min_length=1, max_length=300)
    country: Optional[str] = None
    swift_code: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    rep_email: Optional[str] = None
    is_active: bool = True
    group_ids: List[uuid.UUID] = []


class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    swift_code: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    rep_email: Optional[str] = None
    is_active: Optional[bool] = None
    group_ids: Optional[List[uuid.UUID]] = None


class InstitutionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    institution_type: str
    name: str
    country: Optional[str]
    swift_code: Optional[str]
    website: Optional[str]
    notes: Optional[str]
    rep_name: Optional[str]
    rep_phone: Optional[str]
    rep_email: Optional[str]
    is_active: bool
    group_ids: List[uuid.UUID] = []

    model_config = {"from_attributes": True}
