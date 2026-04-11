"""CreditCard, Purchase, Statement and StatementLine schemas."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.credit_card import CardStatus, StatementStatus, PurchaseStatus, StatementLineType


# ── Card ────────────────────────────────────────────────

class CreditCardCreate(BaseModel):
    card_name: str = Field(..., min_length=1, max_length=200)
    bank_name: str = Field(..., min_length=1, max_length=200)
    card_type: str = Field("CREDIT", max_length=50)
    network: str = Field("VISA", max_length=50)
    last_four_digits: Optional[str] = Field(None, max_length=4)
    credit_limit: Decimal = Field(..., gt=0)
    currency: str = Field(default="TRY", max_length=10)
    statement_day: int = Field(..., ge=1, le=31)
    due_day: int = Field(..., ge=1, le=31)
    group_id: Optional[uuid.UUID] = None
    account_id: Optional[uuid.UUID] = None
    payment_account_id: Optional[uuid.UUID] = None
    expiry_month: Optional[int] = Field(None, ge=1, le=12)
    expiry_year: Optional[int] = None
    notes: Optional[str] = None


class CreditCardUpdate(BaseModel):
    card_name: Optional[str] = None
    credit_limit: Optional[Decimal] = Field(None, gt=0)
    status: Optional[CardStatus] = None
    group_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    statement_day: Optional[int] = Field(None, ge=1, le=31)
    due_day: Optional[int] = Field(None, ge=1, le=31)
    expiry_month: Optional[int] = Field(None, ge=1, le=12)
    expiry_year: Optional[int] = None
    last_four_digits: Optional[str] = Field(None, max_length=4)


class CardSensitiveSave(BaseModel):
    """Save encrypted sensitive card data. Requires current password."""
    password: str
    card_number: Optional[str] = Field(None, min_length=13, max_length=19)
    cvv: Optional[str] = Field(None, min_length=3, max_length=4)


class CardSensitiveReveal(BaseModel):
    """Reveal encrypted sensitive card data. Requires current password."""
    password: str


class CardSensitiveResponse(BaseModel):
    card_number: Optional[str]   # full number
    cvv: Optional[str]
    expiry_month: Optional[int]
    expiry_year: Optional[int]


class CreditCardResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    status: CardStatus
    card_name: str
    bank_name: str
    card_type: str
    network: str
    last_four_digits: Optional[str]
    credit_limit: Decimal
    current_debt: Decimal
    currency: str
    statement_day: int
    due_day: int
    account_id: Optional[uuid.UUID]
    payment_account_id: Optional[uuid.UUID]
    expiry_month: Optional[int]
    expiry_year: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditCardListResponse(BaseModel):
    items: List[CreditCardResponse]
    total: int


# ── Purchase ────────────────────────────────────────────

class PurchaseCreate(BaseModel):
    group_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1, max_length=500)
    total_amount: Decimal = Field(..., gt=0)
    installment_count: int = Field(1, ge=1)
    purchase_date: date
    currency: str = Field(default="TRY", max_length=10)


class PurchaseResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    card_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    description: str
    total_amount: Decimal
    installment_count: int
    installment_amount: Decimal
    currency: str
    purchase_date: date
    remaining_installments: int
    status: PurchaseStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CancelPurchaseRequest(BaseModel):
    scenario: str = Field(..., pattern="^(A|B)$")


# ── Statement ───────────────────────────────────────────

class StatementGenerateRequest(BaseModel):
    period_start: date
    period_end: date
    real_available_limit: Decimal = Field(..., ge=0)


class StatementLineInput(BaseModel):
    category_id: uuid.UUID
    description: str = Field(..., min_length=1, max_length=500)
    amount: Decimal = Field(..., gt=0)


class StatementDetailRequest(BaseModel):
    lines: List[StatementLineInput]


class StatementPayRequest(BaseModel):
    source_account_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)


class StatementLineResponse(BaseModel):
    id: uuid.UUID
    statement_id: uuid.UUID
    purchase_id: Optional[uuid.UUID]
    group_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    line_type: StatementLineType
    description: str
    amount: Decimal
    installment_number: Optional[int]
    total_installments: Optional[int]

    model_config = {"from_attributes": True}


class StatementResponse(BaseModel):
    id: uuid.UUID
    card_id: uuid.UUID
    status: StatementStatus
    period_start: date
    period_end: date
    statement_closing_date: Optional[date]
    due_date: date
    total_spending: Decimal
    minimum_payment: Decimal
    paid_amount: Decimal
    payment_account_id: Optional[uuid.UUID]
    payment_date: Optional[date]
    payment_transaction_id: Optional[uuid.UUID]
    theoretical_available: Decimal
    real_available: Decimal
    new_spending: Decimal
    lines: Optional[List[StatementLineResponse]] = None

    model_config = {"from_attributes": True}


class StatementCreateRequest(BaseModel):
    period_start: date
    period_end: date
    due_date: date


class RecordPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


# ── Limits ──────────────────────────────────────────────

class CardLimitsResponse(BaseModel):
    card_id: uuid.UUID
    total_limit: Decimal
    committed_limit: Decimal
    theoretical_available: Decimal
    current_debt: Decimal
