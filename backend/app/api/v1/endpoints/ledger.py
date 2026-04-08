"""Ledger endpoint — read-only audit view of double-entry accounting records."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.models.user import User
from app.schemas.ledger import LedgerEntryResponse, LedgerBalanceResponse
from app.schemas.common import PagedResponse
from app.services.ledger_service import LedgerService
from app.repositories.account import AccountRepository
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/accounts/{account_id}/entries", response_model=PagedResponse[LedgerEntryResponse])
async def list_ledger_entries(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """
    List all ledger entries for a given account.
    Ledger is read-only — entries are never modified after posting.
    """
    # Verify account belongs to current tenant
    account_repo = AccountRepository(session)
    account = await account_repo.get_by_id_and_tenant(account_id, current_user.tenant_id)
    if not account:
        raise NotFoundError("Account")

    svc = LedgerService(session)
    items, total = await svc.list_by_account(
        account_id=account_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PagedResponse.build(
        items=[LedgerEntryResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/accounts/{account_id}/balance", response_model=LedgerBalanceResponse)
async def get_account_ledger_balance(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """
    Return ledger balance and integrity verification for an account.
    Validates that the account's current_balance matches ledger totals.
    """
    account_repo = AccountRepository(session)
    account = await account_repo.get_by_id_and_tenant(account_id, current_user.tenant_id)
    if not account:
        raise NotFoundError("Account")

    svc = LedgerService(session)
    summary = await svc.get_account_balance_summary(account_id)
    return LedgerBalanceResponse(**summary)


@router.get("/verify/{account_id}", response_model=LedgerBalanceResponse)
async def verify_account_integrity(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """
    Admin-only: verify ledger integrity for an account.
    Returns whether current_balance matches sum of all ledger entries.
    """
    account_repo = AccountRepository(session)
    account = await account_repo.get_by_id_and_tenant(account_id, current_user.tenant_id)
    if not account:
        raise NotFoundError("Account")

    svc = LedgerService(session)
    summary = await svc.get_account_balance_summary(account_id)
    return LedgerBalanceResponse(**summary)
