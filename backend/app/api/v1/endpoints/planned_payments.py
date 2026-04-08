"""PlannedPayment endpoints."""
import uuid
from datetime import date
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, require_permission, get_user_group_ids
from app.models.user import User
from app.models.planned_payment import PlannedPaymentStatus
from app.schemas.planned_payment import (
    PlannedPaymentCreate, PlannedPaymentUpdate, PlannedPaymentResponse,
    MarkPaidRequest,
)
from app.schemas.common import PagedResponse, MessageResponse
from app.services.planned_payment_service import PlannedPaymentService

router = APIRouter(prefix="/planned-payments", tags=["planned-payments"])


@router.get("", response_model=PagedResponse[PlannedPaymentResponse])
async def list_planned_payments(
    current_user: Annotated[User, Depends(require_permission("planned_payments", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    status: Optional[PlannedPaymentStatus] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = PlannedPaymentService(session)
    items, total = await svc.list_by_tenant(
        tenant_id=current_user.tenant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        offset=(page - 1) * page_size,
        limit=page_size,
        group_ids=group_ids or None,
    )
    return PagedResponse.build(
        items=[PlannedPaymentResponse.model_validate(p) for p in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=PlannedPaymentResponse, status_code=201)
async def create_planned_payment(
    body: PlannedPaymentCreate,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "create"))],
    session: AsyncSession = Depends(get_db),
):
    svc = PlannedPaymentService(session)
    results = await svc.create(
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    # Return last created (most future date) so caller sees the series
    return PlannedPaymentResponse.model_validate(results[-1])


@router.get("/{pp_id}", response_model=PlannedPaymentResponse)
async def get_planned_payment(
    pp_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = PlannedPaymentService(session)
    return PlannedPaymentResponse.model_validate(
        await svc.get_by_id(pp_id, current_user.tenant_id)
    )


@router.patch("/{pp_id}", response_model=PlannedPaymentResponse)
async def update_planned_payment(
    pp_id: uuid.UUID,
    body: PlannedPaymentUpdate,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "update"))],
    session: AsyncSession = Depends(get_db),
):
    svc = PlannedPaymentService(session)
    pp = await svc.update(
        pp_id=pp_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return PlannedPaymentResponse.model_validate(pp)


@router.post("/{pp_id}/pay", response_model=PlannedPaymentResponse)
async def mark_paid(
    pp_id: uuid.UUID,
    body: MarkPaidRequest,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Mark a planned payment as paid (full or partial)."""
    svc = PlannedPaymentService(session)
    pp = await svc.mark_paid(
        pp_id=pp_id,
        tenant_id=current_user.tenant_id,
        paid_amount=body.paid_amount,
        linked_transaction_id=body.linked_transaction_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return PlannedPaymentResponse.model_validate(pp)


@router.post("/{pp_id}/cancel", response_model=PlannedPaymentResponse)
async def cancel_planned_payment(
    pp_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "update"))],
    session: AsyncSession = Depends(get_db),
):
    svc = PlannedPaymentService(session)
    pp = await svc.cancel(
        pp_id=pp_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return PlannedPaymentResponse.model_validate(pp)


@router.delete("/{pp_id}", status_code=204)
async def delete_planned_payment(
    pp_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("planned_payments", "delete"))],
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from fastapi import HTTPException

    svc = PlannedPaymentService(session)
    pp = await svc.get_by_id(pp_id, current_user.tenant_id)

    now = datetime.now(timezone.utc)
    check_dt = pp.updated_at if pp.updated_at else pp.created_at
    check_dt_aware = check_dt.replace(tzinfo=timezone.utc) if check_dt.tzinfo is None else check_dt
    if (now - check_dt_aware).days > 5:
        raise HTTPException(
            status_code=400,
            detail="Bu kayıt 5 günlük silme süresi geçtiği için silinemez.",
        )

    await svc.repo.soft_delete(pp)
    await session.commit()


class ExecutePaymentRequest(BaseModel):
    account_id: uuid.UUID
    transaction_date: Optional[date] = None



@router.post("/{pp_id}/execute", response_model=PlannedPaymentResponse)
async def execute_planned_payment(
    pp_id: uuid.UUID,
    body: "ExecutePaymentRequest",
    current_user: Annotated[User, Depends(require_permission("planned_payments", "update"))],
    session: AsyncSession = Depends(get_db),
):
    """Create a real confirmed transaction from a planned payment and mark it paid.

    Loan-generated planned payments are executed as real loan installment payments
    so the liability account and remaining balance stay in sync.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.services.transaction_service import TransactionService
    from app.services.loan_service import LoanService
    from app.schemas.transaction import TransactionCreate
    from app.schemas.loan import InstallmentPayRequest
    from app.models.transaction import TransactionType, TransactionStatus
    from app.models.planned_payment import PlannedPaymentType
    from app.models.loan import Loan, LoanInstallment, LoanStatus, InstallmentStatus

    pp_svc = PlannedPaymentService(session)
    pp = await pp_svc.get_by_id(pp_id, current_user.tenant_id)

    tx_date = body.transaction_date or datetime.now(timezone.utc).date()

    # Loan installment path:
    # Planned loan installments already carry the liability account in pp.account_id
    # and installment number in pp.current_installment.
    if pp.payment_type == PlannedPaymentType.EXPENSE and pp.account_id and pp.current_installment:
        loan_result = await session.execute(
            select(Loan).where(
                Loan.tenant_id == current_user.tenant_id,
                Loan.account_id == pp.account_id,
                Loan.is_deleted == False,
            )
        )
        loan = loan_result.scalar_one_or_none()

        if loan and loan.status == LoanStatus.ACTIVE:
            inst_result = await session.execute(
                select(LoanInstallment).where(
                    LoanInstallment.loan_id == loan.id,
                    LoanInstallment.installment_number == pp.current_installment,
                    LoanInstallment.is_deleted == False,
                )
            )
            inst = inst_result.scalar_one_or_none()

            if inst and inst.status != InstallmentStatus.PAID:
                loan_svc = LoanService(session)
                await loan_svc.pay_installment(
                    loan_id=loan.id,
                    installment_id=inst.id,
                    tenant_id=current_user.tenant_id,
                    data=InstallmentPayRequest(
                        amount=pp.amount,
                        source_account_id=body.account_id,
                        paid_date=tx_date,
                    ),
                    actor_id=current_user.id,
                    actor_email=current_user.email,
                )
                refreshed = await pp_svc.get_by_id(pp_id, current_user.tenant_id)
                await session.commit()
                return PlannedPaymentResponse.model_validate(refreshed)

    # Normal non-loan planned payment flow
    from app.models.planned_payment import PlannedPaymentType

    if pp.payment_type == PlannedPaymentType.EXPENSE:
        tx_type = TransactionType.EXPENSE
        source_id = body.account_id
        target_id = None
    else:
        tx_type = TransactionType.INCOME
        source_id = None
        target_id = body.account_id

    tx_data = TransactionCreate(
        transaction_type=tx_type,
        amount=pp.amount,
        currency=pp.currency,
        source_account_id=source_id,
        target_account_id=target_id,
        category_id=pp.category_id,
        transaction_date=tx_date,
        description=f"Planlı Ödeme: {pp.title}",
        status=TransactionStatus.CONFIRMED,
    )

    tx_svc = TransactionService(session)
    tx = await tx_svc.create(
        tenant_id=current_user.tenant_id,
        group_id=pp.group_id,
        data=tx_data,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )

    pp = await pp_svc.mark_paid(
        pp_id=pp_id,
        tenant_id=current_user.tenant_id,
        linked_transaction_id=tx.id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )

    await session.commit()
    return PlannedPaymentResponse.model_validate(pp)

