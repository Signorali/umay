"""Loan endpoints."""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission, get_user_group_ids
from app.models.user import User
from app.models.loan import LoanStatus
from app.schemas.loan import (
    LoanCreate, LoanUpdate, LoanResponse, LoanListResponse,
    InstallmentPayRequest, InstallmentResponse, EarlyCloseRequest,
)
from app.schemas.common import PagedResponse, MessageResponse
from app.services.loan_service import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("", response_model=PagedResponse[LoanResponse])
async def list_loans(
    current_user: Annotated[User, Depends(require_permission("loans", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    status: Optional[LoanStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = LoanService(session)
    items, total = await svc.list_by_tenant(
        current_user.tenant_id, status=status,
        offset=(page - 1) * page_size, limit=page_size,
        group_ids=group_ids or None,
    )
    return PagedResponse.build(
        items=[LoanResponse.model_validate(l) for l in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=LoanResponse, status_code=201)
async def create_loan(
    body: LoanCreate,
    current_user: Annotated[User, Depends(require_permission("loans", "create"))],
    session: AsyncSession = Depends(get_db),
):
    # Derive group_id from target account if not provided
    if not body.group_id and body.target_account_id:
        from app.models.account import Account
        acc = await session.get(Account, body.target_account_id)
        if acc and acc.group_id:
            body.group_id = acc.group_id

    svc = LoanService(session)
    loan = await svc.create(
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return LoanResponse.model_validate(loan)


@router.get("/{loan_id}", response_model=LoanResponse)
async def get_loan(
    loan_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("loans", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = LoanService(session)
    return LoanResponse.model_validate(
        await svc.get_by_id(loan_id, current_user.tenant_id)
    )


@router.get("/{loan_id}/installments", response_model=list[InstallmentResponse])
async def get_installments(
    loan_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("loans", "view"))],
    session: AsyncSession = Depends(get_db),
):
    """Get the repayment schedule for a loan."""
    svc = LoanService(session)
    installments = await svc.get_installments(loan_id, current_user.tenant_id)
    return [InstallmentResponse.model_validate(i) for i in installments]


@router.post("/{loan_id}/installments/{installment_id}/pay", response_model=InstallmentResponse)
async def pay_installment(
    loan_id: uuid.UUID,
    installment_id: uuid.UUID,
    body: InstallmentPayRequest,
    current_user: Annotated[User, Depends(require_permission("loans", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Record a payment against a loan installment."""
    svc = LoanService(session)
    inst = await svc.pay_installment(
        loan_id=loan_id,
        installment_id=installment_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return InstallmentResponse.model_validate(inst)


@router.post("/{loan_id}/early-close", response_model=LoanResponse)
async def early_close_loan(
    loan_id: uuid.UUID,
    body: EarlyCloseRequest,
    current_user: Annotated[User, Depends(require_permission("loans", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Early closure of a loan. Discount is recorded as interest savings income."""
    svc = LoanService(session)
    loan = await svc.early_close(
        loan_id=loan_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return LoanResponse.model_validate(loan)


@router.post("/{loan_id}/close", response_model=LoanResponse)
async def close_loan(
    loan_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("loans", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Mark a loan as paid off."""
    svc = LoanService(session)
    loan = await svc.close(
        loan_id=loan_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return LoanResponse.model_validate(loan)


@router.delete("/{loan_id}", status_code=204)
async def delete_loan(
    loan_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("loans", "delete"))],
    session: AsyncSession = Depends(get_db),
):
    """Delete a loan and all its traces (if no payments made)."""
    svc = LoanService(session)
    await svc.delete_loan(
        loan_id=loan_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return None
