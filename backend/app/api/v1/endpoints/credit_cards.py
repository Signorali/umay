"""Credit card endpoints."""
import uuid
from datetime import date
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission, get_user_group_ids
from app.models.user import User
from app.models.credit_card import PurchaseStatus
from app.schemas.credit_card import (
    CreditCardCreate, CreditCardUpdate, CreditCardResponse,
    CreditCardListResponse, StatementCreateRequest, StatementResponse,
    RecordPaymentRequest, PurchaseCreate, PurchaseResponse,
    StatementGenerateRequest, StatementDetailRequest, StatementPayRequest,
    CancelPurchaseRequest, CardLimitsResponse, StatementLineResponse,
    CardSensitiveSave, CardSensitiveReveal, CardSensitiveResponse,
)
from app.schemas.common import PagedResponse, MessageResponse
from app.services.credit_card_service import CreditCardService
from app.core.security import verify_password, encrypt_field, decrypt_field
from app.core.exceptions import UnauthorizedError

router = APIRouter(prefix="/credit-cards", tags=["credit-cards"])


# ── Card CRUD ────────────────────────────────────────────

@router.get("", response_model=PagedResponse[CreditCardResponse])
async def list_cards(
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = CreditCardService(session)
    items, total = await svc.list_by_tenant(
        current_user.tenant_id, offset=(page - 1) * page_size, limit=page_size,
        group_ids=group_ids or None,
    )
    return PagedResponse.build(
        items=[CreditCardResponse.model_validate(c) for c in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=CreditCardResponse, status_code=201)
async def create_card(
    body: CreditCardCreate,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "create"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    card = await svc.create(
        tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return CreditCardResponse.model_validate(card)


@router.get("/{card_id}", response_model=CreditCardResponse)
async def get_card(
    card_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    return CreditCardResponse.model_validate(
        await svc.get_by_id(card_id, current_user.tenant_id)
    )


@router.patch("/{card_id}", response_model=CreditCardResponse)
async def update_card(
    card_id: uuid.UUID,
    body: CreditCardUpdate,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "create"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    card = await svc.update(
        card_id=card_id, tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return CreditCardResponse.model_validate(card)


# ── Sensitive Data ───────────────────────────────────────

@router.post("/{card_id}/sensitive/save", response_model=dict)
async def save_sensitive_data(
    card_id: uuid.UUID,
    body: CardSensitiveSave,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "create"))],
    session: AsyncSession = Depends(get_db),
):
    """Save encrypted card number and CVV. Requires current password."""
    if not verify_password(body.password, current_user.hashed_password):
        raise UnauthorizedError("Şifre yanlış")
    svc = CreditCardService(session)
    card = await svc.get_by_id(card_id, current_user.tenant_id)
    updates: dict = {}
    if body.card_number is not None:
        updates["card_number_encrypted"] = encrypt_field(body.card_number)
        updates["last_four_digits"] = body.card_number[-4:]
    if body.cvv is not None:
        updates["cvv_encrypted"] = encrypt_field(body.cvv)
    if updates:
        await svc.repo.update(card, **updates)
        await session.commit()
    return {"ok": True}


@router.post("/{card_id}/sensitive/reveal", response_model=CardSensitiveResponse)
async def reveal_sensitive_data(
    card_id: uuid.UUID,
    body: CardSensitiveReveal,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    """Reveal encrypted card data. Requires current password."""
    if not verify_password(body.password, current_user.hashed_password):
        raise UnauthorizedError("Şifre yanlış")
    svc = CreditCardService(session)
    card = await svc.get_by_id(card_id, current_user.tenant_id)
    return CardSensitiveResponse(
        card_number=decrypt_field(card.card_number_encrypted) if card.card_number_encrypted else None,
        cvv=decrypt_field(card.cvv_encrypted) if card.cvv_encrypted else None,
        expiry_month=card.expiry_month,
        expiry_year=card.expiry_year,
    )


# ── Limits ───────────────────────────────────────────────

@router.get("/{card_id}/limits", response_model=CardLimitsResponse)
async def get_card_limits(
    card_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    at_date: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    return await svc.get_limits(card_id, current_user.tenant_id, at_date=at_date)


# ── Purchases ────────────────────────────────────────────

@router.post("/{card_id}/purchases", response_model=PurchaseResponse, status_code=201)
async def create_purchase(
    card_id: uuid.UUID,
    body: PurchaseCreate,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    purchase = await svc.create_purchase(
        card_id=card_id, tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return PurchaseResponse.model_validate(purchase)


@router.get("/{card_id}/purchases", response_model=PagedResponse[PurchaseResponse])
async def list_purchases(
    card_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
    status: Optional[PurchaseStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = CreditCardService(session)
    items, total = await svc.list_purchases(
        card_id=card_id, tenant_id=current_user.tenant_id,
        status=status, offset=(page - 1) * page_size, limit=page_size,
    )
    return PagedResponse.build(
        items=[PurchaseResponse.model_validate(p) for p in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/{card_id}/purchases/{purchase_id}/cancel", response_model=PurchaseResponse)
async def cancel_purchase(
    card_id: uuid.UUID,
    purchase_id: uuid.UUID,
    body: CancelPurchaseRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    purchase = await svc.cancel_purchase(
        card_id=card_id, purchase_id=purchase_id,
        tenant_id=current_user.tenant_id, scenario=body.scenario,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return PurchaseResponse.model_validate(purchase)


# ── Statements ───────────────────────────────────────────

@router.get("/{card_id}/statements", response_model=PagedResponse[StatementResponse])
async def list_statements(
    card_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
):
    svc = CreditCardService(session)
    items, total = await svc.list_statements(
        card_id=card_id, tenant_id=current_user.tenant_id,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return PagedResponse.build(
        items=[StatementResponse.model_validate(s) for s in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{card_id}/statements/{statement_id}", response_model=StatementResponse)
async def get_statement_detail(
    card_id: uuid.UUID,
    statement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    stmt = await svc.get_statement_detail(card_id, statement_id, current_user.tenant_id)
    resp = StatementResponse.model_validate(stmt)
    resp.lines = [StatementLineResponse.model_validate(l) for l in (stmt.lines or [])]
    return resp


@router.post("/{card_id}/statements/preview")
async def preview_statement(
    card_id: uuid.UUID,
    body: StatementGenerateRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    """Dry-run: returns estimated statement totals without saving."""
    svc = CreditCardService(session)
    result = await svc.preview_statement(
        card_id=card_id, tenant_id=current_user.tenant_id, data=body,
    )
    return result


@router.post("/{card_id}/statements/generate", response_model=StatementResponse, status_code=201)
async def generate_statement(
    card_id: uuid.UUID,
    body: StatementGenerateRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    stmt = await svc.generate_statement(
        card_id=card_id, tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return StatementResponse.model_validate(stmt)


@router.post("/{card_id}/statements/{statement_id}/detail", response_model=StatementResponse)
async def detail_new_spending(
    card_id: uuid.UUID,
    statement_id: uuid.UUID,
    body: StatementDetailRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    stmt = await svc.detail_new_spending(
        card_id=card_id, statement_id=statement_id,
        tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    result = await svc.get_statement_detail(card_id, statement_id, current_user.tenant_id)
    resp = StatementResponse.model_validate(result)
    resp.lines = [StatementLineResponse.model_validate(l) for l in (result.lines or [])]
    return resp


@router.delete("/{card_id}/statements/{statement_id}", response_model=MessageResponse)
async def delete_statement(
    card_id: uuid.UUID,
    statement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    await svc.delete_statement(
        card_id=card_id, statement_id=statement_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Statement deleted")


@router.post("/{card_id}/statements/{statement_id}/finalize", response_model=StatementResponse)
async def finalize_statement(
    card_id: uuid.UUID,
    statement_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    stmt = await svc.finalize_statement(
        card_id=card_id, statement_id=statement_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return StatementResponse.model_validate(stmt)


@router.post("/{card_id}/statements/{statement_id}/pay", response_model=StatementResponse)
async def pay_statement(
    card_id: uuid.UUID,
    statement_id: uuid.UUID,
    body: StatementPayRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    stmt = await svc.pay_statement(
        card_id=card_id, statement_id=statement_id,
        tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return StatementResponse.model_validate(stmt)


# ── Legacy compat ────────────────────────────────────────

@router.post("/{card_id}/statements", response_model=StatementResponse, status_code=201)
async def create_statement(
    card_id: uuid.UUID,
    body: StatementCreateRequest,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    statement = await svc.create_statement(
        card_id=card_id, tenant_id=current_user.tenant_id, data=body,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return StatementResponse.model_validate(statement)


@router.post("/{card_id}/statements/close", response_model=StatementResponse)
async def close_statement(
    card_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("credit_cards", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CreditCardService(session)
    open_stmt = await svc.statement_repo.get_open_statement(card_id)
    if not open_stmt:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Open statement")
    stmt = await svc.finalize_statement(
        card_id=card_id, statement_id=open_stmt.id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id, actor_email=current_user.email,
    )
    await session.commit()
    return StatementResponse.model_validate(stmt)
