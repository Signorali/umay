"""Transaction schemas."""
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from app.models.transaction import TransactionType, TransactionStatus


class TransactionCreate(BaseModel):
    transaction_type: TransactionType
    status: TransactionStatus = TransactionStatus.DRAFT
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="TRY", max_length=10)
    source_account_id: Optional[uuid.UUID] = None
    target_account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    transaction_date: date
    value_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    # Set to True for system-generated transactions (e.g. credit card payments)
    # that don't require a user-assigned category.
    system_generated: bool = False

    @model_validator(mode="after")
    def validate_accounts(self) -> "TransactionCreate":
        tx_type = self.transaction_type
        if tx_type == TransactionType.INCOME and not self.target_account_id:
            raise ValueError("INCOME transaction requires a target_account_id")
        if tx_type == TransactionType.EXPENSE and not self.source_account_id:
            raise ValueError("EXPENSE transaction requires a source_account_id")
        if tx_type == TransactionType.TRANSFER:
            if not self.source_account_id or not self.target_account_id:
                raise ValueError("TRANSFER requires both source_account_id and target_account_id")
        # Category is required for user-created INCOME and EXPENSE transactions
        if not self.system_generated and tx_type in (TransactionType.INCOME, TransactionType.EXPENSE) and not self.category_id:
            raise ValueError("Gelir ve gider işlemleri için kategori zorunludur")
        return self


class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    reference_number: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    value_date: Optional[date] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    transaction_type: TransactionType
    status: TransactionStatus
    amount: Decimal
    currency: str
    source_account_id: Optional[uuid.UUID]
    target_account_id: Optional[uuid.UUID]
    # Account and group names for display
    source_account_name: Optional[str] = None
    target_account_name: Optional[str] = None
    source_group_name: Optional[str] = None
    target_group_name: Optional[str] = None
    category_id: Optional[uuid.UUID]
    transaction_date: date
    value_date: Optional[date]
    description: Optional[str]
    notes: Optional[str]
    reference_number: Optional[str]
    reversed_by_id: Optional[uuid.UUID]
    reversal_of_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int


class ConfirmTransactionRequest(BaseModel):
    pass  # No body needed; action is implicit


class ReverseTransactionRequest(BaseModel):
    description: Optional[str] = None
