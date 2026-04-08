"""Ledger schemas."""
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    entry_type: str
    amount: Decimal
    currency: str
    posted_at: datetime
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerBalanceResponse(BaseModel):
    account_id: uuid.UUID
    ledger_balance: Decimal
    is_balanced: bool
