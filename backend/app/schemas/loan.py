"""Loan and LoanInstallment schemas."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.loan import LoanStatus, InstallmentStatus


class LoanCreate(BaseModel):
    lender_name: str = Field(..., min_length=1, max_length=300)
    loan_purpose: Optional[str] = None
    principal: Decimal = Field(..., gt=0)
    disbursed_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(default=Decimal("0"), ge=0)
    total_interest: Decimal = Field(default=Decimal("0"), ge=0)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="TRY", max_length=10)
    term_months: int = Field(..., gt=0)
    start_date: date
    maturity_date: Optional[date] = None
    group_id: Optional[uuid.UUID] = None
    category_id: uuid.UUID = Field(..., description="Taksit işlemleri için kategori (zorunlu)")
    payment_day: int = Field(..., ge=1, le=31)
    installment_amount: Decimal = Field(..., gt=0)
    target_account_id: uuid.UUID = Field(...)
    notes: Optional[str] = None


class LoanUpdate(BaseModel):
    lender_name: Optional[str] = None
    loan_purpose: Optional[str] = None
    notes: Optional[str] = None


class LoanResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    status: LoanStatus
    lender_name: str
    loan_purpose: Optional[str]
    principal: Decimal
    disbursed_amount: Decimal
    interest_rate: Decimal
    total_interest: Decimal
    fees: Decimal
    currency: str
    term_months: int
    payment_day: int
    installment_amount: Decimal
    start_date: date
    maturity_date: Optional[date]
    total_paid: Decimal
    remaining_balance: Decimal
    account_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanListResponse(BaseModel):
    items: List[LoanResponse]
    total: int


class InstallmentPayRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    source_account_id: uuid.UUID = Field(...)
    paid_date: Optional[date] = None
    linked_transaction_id: Optional[uuid.UUID] = None
    # Faiz indirimi (erken ödeme) — tutarın ne kadarı banka tarafından indirildi
    interest_discount: Optional[Decimal] = Field(default=None, ge=0)
    # Gecikme faizi — geç ödeme cezası tutarı
    late_interest: Optional[Decimal] = Field(default=None, ge=0)
    late_interest_category_id: Optional[uuid.UUID] = None


class EarlyCloseRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    source_account_id: uuid.UUID = Field(...)
    close_date: Optional[date] = None


class InstallmentResponse(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    installment_number: int
    due_date: date
    principal_amount: Decimal
    interest_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    paid_date: Optional[date]
    status: InstallmentStatus
    linked_transaction_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}
