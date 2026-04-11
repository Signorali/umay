"""PlannedPayment schemas."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator

from app.models.planned_payment import PlannedPaymentType, PlannedPaymentStatus, RecurrenceRule


class PlannedPaymentCreate(BaseModel):
    payment_type: PlannedPaymentType
    title: str = Field(..., min_length=1, max_length=300)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="TRY", max_length=10)
    group_id: Optional[uuid.UUID] = None
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    planned_date: date
    due_date: Optional[date] = None
    reminder_date: Optional[date] = None
    recurrence_rule: RecurrenceRule = RecurrenceRule.NONE
    recurrence_end_date: Optional[date] = None
    total_installments: Optional[int] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_required_fields(self) -> "PlannedPaymentCreate":
        if not self.account_id:
            raise ValueError("Planlı ödeme için hesap seçimi zorunludur")
        if not self.category_id:
            raise ValueError("Planlı ödeme için kategori seçimi zorunludur")
        return self



class PlannedPaymentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    amount: Optional[Decimal] = Field(None, gt=0)
    planned_date: Optional[date] = None
    due_date: Optional[date] = None
    reminder_date: Optional[date] = None
    notes: Optional[str] = None


class MarkPaidRequest(BaseModel):
    paid_amount: Optional[Decimal] = Field(None, gt=0)
    linked_transaction_id: Optional[uuid.UUID] = None


class PlannedPaymentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    payment_type: PlannedPaymentType
    status: PlannedPaymentStatus
    title: str
    amount: Decimal
    currency: str
    paid_amount: Decimal
    account_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    planned_date: date
    due_date: Optional[date]
    reminder_date: Optional[date]
    recurrence_rule: RecurrenceRule
    total_installments: Optional[int]
    current_installment: Optional[int]
    linked_transaction_id: Optional[uuid.UUID]
    credit_card_purchase_id: Optional[uuid.UUID]
    loan_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlannedPaymentListResponse(BaseModel):
    items: list[PlannedPaymentResponse]
    total: int
