"""Account endpoints."""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission, get_user_group_ids
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse
from app.schemas.common import PagedResponse, MessageResponse
from app.services.account_service import AccountService
from app.models.group import Group
from app.models.institution import InstitutionGroupLink
from app.utils.text_normalization import normalize_form_text
from sqlalchemy import select

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _can_access_account(account, current_user, group_ids) -> bool:
    """Return True if user is allowed to view/edit this account."""
    if current_user.is_tenant_admin or current_user.is_superuser:
        return True
    if account.group_id is None:
        return True
    return account.group_id in (group_ids or [])


async def _add_group_name(account, response: AccountResponse, session: AsyncSession) -> AccountResponse:
    """Populate group_name in AccountResponse."""
    if account.group_id:
        group_result = await session.execute(select(Group.name).where(Group.id == account.group_id))
        response.group_name = group_result.scalar_one_or_none()
    return response


@router.get("", response_model=PagedResponse[AccountResponse])
async def list_accounts(
    current_user: Annotated[User, Depends(require_permission("accounts", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = AccountService(session)
    # Always fetch ALL tenant accounts (no group_ids filter).
    # Balance visibility is controlled via is_own_group flag below.
    items, total = await svc.list_by_tenant(
        current_user.tenant_id,
        offset=(page - 1) * page_size,
        limit=page_size,
        group_ids=None,
    )
    is_admin = current_user.is_tenant_admin or current_user.is_superuser
    own_group_set = set(group_ids or [])

    # For INVESTMENT accounts tied to institutions, check institution_group_links
    inst_ids = [a.institution_id for a in items if getattr(a, 'institution_id', None) and a.account_type == 'INVESTMENT']
    inst_group_map: dict = {}       # institution_id -> set of group UUIDs
    inst_group_names_map: dict = {} # institution_id -> list of group names
    if inst_ids:
        rows = (await session.execute(
            select(InstitutionGroupLink.institution_id, InstitutionGroupLink.group_id, Group.name)
            .join(Group, Group.id == InstitutionGroupLink.group_id)
            .where(InstitutionGroupLink.institution_id.in_(inst_ids))
        )).all()
        for row in rows:
            inst_group_map.setdefault(row.institution_id, set()).add(row.group_id)
            inst_group_names_map.setdefault(row.institution_id, []).append(row.name)

    responses = []
    for a in items:
        resp = await _add_group_name(a, AccountResponse.model_validate(a), session)
        inst_id = getattr(a, 'institution_id', None)
        inst_groups = inst_group_map.get(inst_id, set())
        resp.is_own_group = (
            is_admin
            or (a.group_id is None and not inst_groups)
            or (a.group_id in own_group_set)
            or bool(inst_groups & own_group_set)
        )
        # Populate group_names: prefer institution groups for INVESTMENT accounts
        if inst_id and a.account_type == 'INVESTMENT' and inst_id in inst_group_names_map:
            resp.group_names = inst_group_names_map[inst_id]
        elif resp.group_name:
            resp.group_names = [resp.group_name]
        responses.append(resp)
    return PagedResponse.build(
        items=responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    body: AccountCreate,
    current_user: Annotated[User, Depends(require_permission("accounts", "create"))],
    session: AsyncSession = Depends(get_db),
):
    # Normalize text fields
    normalized_body = body.model_copy(update={
        'name': normalize_form_text(body.name),
        'institution_name': normalize_form_text(body.institution_name) if body.institution_name else None,
    })
    svc = AccountService(session)
    account = await svc.create(
        tenant_id=current_user.tenant_id,
        data=normalized_body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    resp = AccountResponse.model_validate(account)
    return await _add_group_name(account, resp, session)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("accounts", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    svc = AccountService(session)
    account = await svc.get_by_id(account_id, current_user.tenant_id)
    if not _can_access_account(account, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Access denied to this account")
    resp = AccountResponse.model_validate(account)
    return await _add_group_name(account, resp, session)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    current_user: Annotated[User, Depends(require_permission("accounts", "update"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    svc = AccountService(session)
    account = await svc.get_by_id(account_id, current_user.tenant_id)
    if not _can_access_account(account, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Access denied to this account")
    account = await svc.update(
        account_id=account_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    resp = AccountResponse.model_validate(account)
    return await _add_group_name(account, resp, session)


@router.delete("/{account_id}", response_model=MessageResponse)
async def delete_account(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("accounts", "delete"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
):
    from fastapi import HTTPException
    svc = AccountService(session)
    account = await svc.get_by_id(account_id, current_user.tenant_id)
    if not _can_access_account(account, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Access denied to this account")
    await svc.delete(
        account_id=account_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Account deleted successfully")


@router.get("/{account_id}/transactions")
async def list_account_transactions(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("accounts", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get all transactions for a specific account with filters."""
    from datetime import date as date_type
    from app.models.transaction import Transaction, TransactionType as TxType, TransactionStatus
    from sqlalchemy import select, func, or_

    from fastapi import HTTPException
    svc = AccountService(session)
    account = await svc.get_by_id(account_id, current_user.tenant_id)
    if not _can_access_account(account, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Access denied to this account")

    filters = [
        or_(
            Transaction.source_account_id == account_id,
            Transaction.target_account_id == account_id,
        ),
        Transaction.tenant_id == current_user.tenant_id,
        Transaction.is_deleted == False,
    ]

    if date_from:
        filters.append(Transaction.transaction_date >= date_type.fromisoformat(date_from))
    if date_to:
        filters.append(Transaction.transaction_date <= date_type.fromisoformat(date_to))
    if transaction_type:
        filters.append(Transaction.transaction_type == transaction_type)

    count_q = select(func.count(Transaction.id)).where(*filters)
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    data_q = (
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(data_q)
    items = result.scalars().all()

    from app.schemas.transaction import TransactionResponse
    from app.schemas.common import PagedResponse
    return PagedResponse.build(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{account_id}/profit")
async def get_account_profit(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("accounts", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
):
    """Calculate net profit/loss for an account.

    Net Profit = Current Balance - Opening Balance - Net Capital Flows
    Net Capital = (Incoming Transfers) - (Outgoing Transfers)
    """
    from fastapi import HTTPException
    from decimal import Decimal
    from app.models.transaction import Transaction, TransactionType as TxType
    from sqlalchemy import select, func

    svc = AccountService(session)
    account = await svc.get_by_id(account_id, current_user.tenant_id)
    if not _can_access_account(account, current_user, group_ids):
        raise HTTPException(status_code=403, detail="Access denied to this account")

    # Sum of incoming transfers (money deposited into this account from another)
    in_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.target_account_id == account_id,
        Transaction.tenant_id == current_user.tenant_id,
        Transaction.transaction_type == TxType.TRANSFER,
        Transaction.is_deleted == False,
    )
    total_transfers_in = Decimal(str((await session.execute(in_q)).scalar_one()))

    # Sum of outgoing transfers (money withdrawn from this account)
    out_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.source_account_id == account_id,
        Transaction.tenant_id == current_user.tenant_id,
        Transaction.transaction_type == TxType.TRANSFER,
        Transaction.is_deleted == False,
    )
    total_transfers_out = Decimal(str((await session.execute(out_q)).scalar_one()))

    net_capital = total_transfers_in - total_transfers_out
    current_balance = Decimal(str(account.current_balance))
    opening_balance = Decimal(str(account.opening_balance or 0))
    net_profit = current_balance - opening_balance - net_capital

    return {
        "net_profit": float(net_profit),
        "net_capital": float(net_capital),
        "current_balance": float(current_balance),
        "opening_balance": float(opening_balance),
        "total_transfers_in": float(total_transfers_in),
        "total_transfers_out": float(total_transfers_out),
    }
