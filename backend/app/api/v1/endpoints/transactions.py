"""Transaction endpoints — with confirm/cancel/reverse lifecycle."""
import uuid
from datetime import date
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission, get_user_group_ids
from app.models.user import User
from app.models.transaction import TransactionType, TransactionStatus
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    TransactionListResponse, ReverseTransactionRequest,
)
from app.schemas.common import PagedResponse, MessageResponse
from app.services.transaction_service import TransactionService
from app.models.category import Category

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _populate_response_names(session: AsyncSession, tx) -> dict:
    """Populate account and group names for a transaction response."""
    from app.models.account import Account
    from app.models.group import Group

    tx_dict = TransactionResponse.model_validate(tx).model_dump()

    if tx.source_account_id:
        src_acct = await session.get(Account, tx.source_account_id)
        if src_acct:
            tx_dict['source_account_name'] = src_acct.name
            src_group = await session.get(Group, src_acct.group_id)
            if src_group:
                tx_dict['source_group_name'] = src_group.name

    if tx.target_account_id:
        tgt_acct = await session.get(Account, tx.target_account_id)
        if tgt_acct:
            tx_dict['target_account_name'] = tgt_acct.name
            tgt_group = await session.get(Group, tgt_acct.group_id)
            if tgt_group:
                tx_dict['target_group_name'] = tgt_group.name

    return tx_dict


@router.get("", response_model=PagedResponse[TransactionResponse])
async def list_transactions(
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    status: Optional[TransactionStatus] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    account_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """List transactions. Regular users see only their group's transactions."""
    svc = TransactionService(session)
    items, total = await svc.list_by_tenant(
        tenant_id=current_user.tenant_id,
        status=status,
        transaction_type=transaction_type,
        date_from=date_from,
        date_to=date_to,
        account_id=account_id,
        group_ids=group_ids if group_ids else None,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    # Build response with account/group names
    from sqlalchemy import select
    from app.models.account import Account
    from app.models.group import Group

    response_items = []
    for tx in items:
        tx_dict = TransactionResponse.model_validate(tx).model_dump()

        # Get account and group names
        if tx.source_account_id:
            src_acct = await session.get(Account, tx.source_account_id)
            if src_acct:
                tx_dict['source_account_name'] = src_acct.name
                src_group = await session.get(Group, src_acct.group_id)
                if src_group:
                    tx_dict['source_group_name'] = src_group.name

        if tx.target_account_id:
            tgt_acct = await session.get(Account, tx.target_account_id)
            if tgt_acct:
                tx_dict['target_account_name'] = tgt_acct.name
                tgt_group = await session.get(Group, tgt_acct.group_id)
                if tgt_group:
                    tx_dict['target_group_name'] = tgt_group.name

        response_items.append(TransactionResponse.model_validate(tx_dict))

    return PagedResponse.build(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    current_user: Annotated[User, Depends(require_permission("transactions", "create"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
):
    """Create a transaction."""
    svc = TransactionService(session)
    # Derive group_id from the selected category's group_id so that
    # users in multiple groups can create transactions for any group's category.
    group_id: Optional[uuid.UUID] = None
    if body.category_id:
        from sqlalchemy import select
        cat_result = await session.execute(
            select(Category.group_id).where(Category.id == body.category_id)
        )
        group_id = cat_result.scalar_one_or_none()
    if group_id is None and group_ids:
        group_id = group_ids[0]  # fallback for transfers (no category)
    tx = await svc.create(
        tenant_id=current_user.tenant_id,
        group_id=group_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    tx_dict = await _populate_response_names(session, tx)
    return TransactionResponse.model_validate(tx_dict)


@router.get("/{tx_id}", response_model=TransactionResponse)
async def get_transaction(
    tx_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = TransactionService(session)
    tx = await svc.get_by_id(tx_id, current_user.tenant_id)
    tx_dict = await _populate_response_names(session, tx)
    return TransactionResponse.model_validate(tx_dict)


@router.patch("/{tx_id}", response_model=TransactionResponse)
async def update_transaction(
    tx_id: uuid.UUID,
    body: TransactionUpdate,
    current_user: Annotated[User, Depends(require_permission("transactions", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Update a DRAFT transaction."""
    svc = TransactionService(session)
    tx = await svc.update(
        tx_id=tx_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    tx_dict = await _populate_response_names(session, tx)
    return TransactionResponse.model_validate(tx_dict)


@router.post("/{tx_id}/confirm", response_model=TransactionResponse)
async def confirm_transaction(
    tx_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "approve"))],
    session: AsyncSession = Depends(get_db),
):
    """Confirm a DRAFT transaction. Posts ledger entries."""
    svc = TransactionService(session)
    tx = await svc.confirm(
        tx_id=tx_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    tx_dict = await _populate_response_names(session, tx)
    return TransactionResponse.model_validate(tx_dict)


@router.post("/{tx_id}/cancel", response_model=TransactionResponse)
async def cancel_transaction(
    tx_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Cancel a DRAFT transaction."""
    svc = TransactionService(session)
    tx = await svc.cancel(
        tx_id=tx_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    tx_dict = await _populate_response_names(session, tx)
    return TransactionResponse.model_validate(tx_dict)


@router.post("/{tx_id}/reverse", response_model=TransactionResponse)
async def reverse_transaction(
    tx_id: uuid.UUID,
    body: ReverseTransactionRequest,
    current_user: Annotated[User, Depends(require_permission("transactions", "approve"))],
    session: AsyncSession = Depends(get_db),
):
    svc = TransactionService(session)
    reversal = await svc.reverse(
        tx_id=tx_id,
        tenant_id=current_user.tenant_id,
        description=body.description,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return TransactionResponse.model_validate(reversal)


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "delete"))],
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.transaction import Transaction

    row = await session.execute(
        select(Transaction.created_at).where(
            Transaction.id == tx_id,
            Transaction.tenant_id == current_user.tenant_id,
            Transaction.is_deleted == False,
        )
    )
    created_at = row.scalar_one_or_none()
    if created_at is not None:
        now = datetime.now(timezone.utc)
        ca = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        if (now - ca).days > 5:
            raise HTTPException(
                status_code=400,
                detail="Bu işlem 5 günlük silme süresi geçtiği için silinemez.",
            )

    svc = TransactionService(session)
    await svc.delete(
        tx_id=tx_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
