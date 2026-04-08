"""Report request/response schemas."""
import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ReportPeriodParams(BaseModel):
    period_start: date
    period_end: date
    group_id: Optional[uuid.UUID] = None


class IncomeExpenseReportResponse(BaseModel):
    income: dict
    expense: dict
    transfer: dict
    net: float
    period: dict


class AccountMovementResponse(BaseModel):
    account_id: str
    account_name: str
    currency: str
    current_balance: float
    period: dict
    debits: dict
    credits: dict
    net: float


class CategoryBreakdownItem(BaseModel):
    category_id: Optional[str]
    total: float
    count: int


class CashFlowItem(BaseModel):
    date: str
    type: str
    title: str
    amount: float
    currency: str
    status: str


class LoanReportResponse(BaseModel):
    active_loan_count: int
    total_principal: dict
    total_remaining: dict
    overdue_installments: int


class CreditCardReportResponse(BaseModel):
    card_count: int
    total_limit: dict
    total_debt: dict
    utilization: dict
    overdue_statements: int
