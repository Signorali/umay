"""Symbol-based obligation endpoints (borç / alacak)."""
import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, condecimal

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.obligation import SymbolObligation, ObligationDirection, ObligationCounterpartyType, ObligationStatus
from app.models.user import User

router = APIRouter(prefix="/obligations", tags=["obligations"])


class ObligationCreate(BaseModel):
    symbol: str
    label: str
    quantity: float
    price_per_unit: Optional[float] = None
    currency: str = "TRY"
    direction: ObligationDirection          # BORROW | LEND
    counterparty_type: ObligationCounterpartyType  # EXTERNAL | USER
    counterparty_user_id: Optional[uuid.UUID] = None
    counterparty_name: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class ObligationStatusUpdate(BaseModel):
    status: ObligationStatus


def _serialize(o: SymbolObligation) -> dict:
    return {
        "id": str(o.id),
        "symbol": o.symbol,
        "label": o.label,
        "quantity": float(o.quantity),
        "price_per_unit": float(o.price_per_unit) if o.price_per_unit else None,
        "currency": o.currency,
        "direction": o.direction,
        "counterparty_type": o.counterparty_type,
        "counterparty_user_id": str(o.counterparty_user_id) if o.counterparty_user_id else None,
        "counterparty_name": o.counterparty_name,
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "status": o.status,
        "peer_obligation_id": str(o.peer_obligation_id) if o.peer_obligation_id else None,
        "notes": o.notes,
        "created_at": o.created_at.isoformat(),
    }


@router.get("")
async def list_obligations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "view")),
):
    """Kullanıcının tüm borç/alacak kayıtları."""
    q = select(SymbolObligation).where(
        SymbolObligation.user_id == current_user.id,
        SymbolObligation.is_deleted == False,
    ).order_by(SymbolObligation.due_date.asc().nullslast(), SymbolObligation.created_at.desc())
    result = await db.execute(q)
    items = result.scalars().all()
    return [_serialize(i) for i in items]


@router.post("", status_code=201)
async def create_obligation(
    body: ObligationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "manage")),
):
    """
    Borç veya alacak kaydı oluştur.
    Karşı taraf sistem kullanıcısı ise otomatik ters kayıt oluşturulur.
    """
    # Karşı taraf USER ise o kullanıcıyı bul
    peer_user = None
    counterparty_name = body.counterparty_name

    if body.counterparty_type == ObligationCounterpartyType.USER:
        if not body.counterparty_user_id:
            raise HTTPException(status_code=400, detail="Kullanıcı borç/alacağı için counterparty_user_id gerekli.")
        r = await db.execute(select(User).where(User.id == body.counterparty_user_id, User.is_deleted == False))
        peer_user = r.scalars().first()
        if not peer_user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        counterparty_name = peer_user.full_name or peer_user.email

    # Ana kayıt
    obligation = SymbolObligation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        symbol=body.symbol.upper(),
        label=body.label,
        quantity=body.quantity,
        price_per_unit=body.price_per_unit,
        currency=body.currency,
        direction=body.direction,
        counterparty_type=body.counterparty_type,
        counterparty_user_id=body.counterparty_user_id,
        counterparty_name=counterparty_name,
        due_date=body.due_date,
        notes=body.notes,
    )
    db.add(obligation)
    await db.flush()  # ID al

    # Ters kayıt (peer)
    if peer_user:
        reverse_direction = ObligationDirection.LEND if body.direction == ObligationDirection.BORROW else ObligationDirection.BORROW
        peer = SymbolObligation(
            tenant_id=peer_user.tenant_id,
            user_id=peer_user.id,
            symbol=body.symbol.upper(),
            label=body.label,
            quantity=body.quantity,
            price_per_unit=body.price_per_unit,
            currency=body.currency,
            direction=reverse_direction,
            counterparty_type=ObligationCounterpartyType.USER,
            counterparty_user_id=current_user.id,
            counterparty_name=current_user.full_name or current_user.email,
            due_date=body.due_date,
            notes=body.notes,
            peer_obligation_id=obligation.id,
        )
        db.add(peer)
        await db.flush()
        obligation.peer_obligation_id = peer.id

    await db.commit()
    await db.refresh(obligation)
    return _serialize(obligation)


@router.patch("/{obligation_id}/status")
async def update_obligation_status(
    obligation_id: uuid.UUID,
    body: ObligationStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "manage")),
):
    """Borç/alacak durumunu güncelle (SETTLED / CANCELLED). Peer kaydını da günceller."""
    r = await db.execute(
        select(SymbolObligation).where(
            SymbolObligation.id == obligation_id,
            SymbolObligation.user_id == current_user.id,
            SymbolObligation.is_deleted == False,
        )
    )
    item = r.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")

    item.status = body.status

    # Peer kaydını da güncelle
    if item.peer_obligation_id:
        r2 = await db.execute(
            select(SymbolObligation).where(SymbolObligation.id == item.peer_obligation_id)
        )
        peer = r2.scalars().first()
        if peer:
            peer.status = body.status

    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.delete("/{obligation_id}", status_code=204)
async def delete_obligation(
    obligation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("market", "manage")),
):
    r = await db.execute(
        select(SymbolObligation).where(
            SymbolObligation.id == obligation_id,
            SymbolObligation.user_id == current_user.id,
            SymbolObligation.is_deleted == False,
        )
    )
    item = r.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    item.is_deleted = True
    await db.commit()
