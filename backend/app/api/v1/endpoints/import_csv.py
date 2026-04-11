"""
Import endpoints — CSV upload for transactions and accounts.

Flow:
  1. POST /import/transactions/preview  → parse & validate (no DB write)
  2. POST /import/transactions          → actually import as DRAFT
  3. POST /import/accounts/preview      → parse & validate (no DB write)
  4. POST /import/accounts              → actually create accounts

Admin or authenticated user required.
File size limit: MAX_UPLOAD_SIZE_MB from settings.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.models.user import User
from app.models.transaction import TransactionStatus
from app.services.import_service import ImportService
from app.core.config import settings

router = APIRouter(prefix="/import", tags=["import"])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


async def _read_csv(file: UploadFile) -> bytes:
    """Read upload, validate content-type and size."""
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "text/plain"):
        # Allow any; just read it — let the parser fail gracefully
        pass
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Dosya boyutu {settings.MAX_UPLOAD_SIZE_MB}MB sınırını aşıyor",
        )
    return content


# ─── Transaction import ───────────────────────────────────────────────────────

@router.post("/transactions/preview")
async def preview_transaction_import(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="CSV dosyası (UTF-8 veya UTF-8-BOM)"),
):
    """
    Parse a transaction CSV and return a preview with validation results.
    No data is written to the database.

    Expected columns (TR or EN):
      date/tarih, type/tür, amount/tutar, currency, description/açıklama,
      source_account/kaynak hesap, target_account/hedef hesap, category/kategori,
      reference/referans, notes/notlar
    """
    content = await _read_csv(file)
    svc = ImportService(session)
    preview = await svc.preview_transactions(content, current_user.tenant_id)
    return preview.dict()


@router.post("/transactions", status_code=201)
async def import_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="CSV dosyası"),
    as_draft: bool = Query(True, description="True: DRAFT olarak oluştur, False: CONFIRMED"),
):
    """
    Import transactions from CSV. Default: DRAFT status (user must confirm each).
    Set as_draft=False to confirm all immediately (admin recommended).
    """
    content = await _read_csv(file)
    svc = ImportService(session)
    status = TransactionStatus.DRAFT if as_draft else TransactionStatus.CONFIRMED
    result = await svc.import_transactions(
        content,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        status=status,
    )
    await session.commit()
    return result


# ─── Account import ───────────────────────────────────────────────────────────

@router.post("/accounts/preview")
async def preview_account_import(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Parse an account CSV and return a validation preview.

    Expected columns (TR or EN):
      name/ad, type/tür, currency, opening_balance/başlangıç bakiyesi,
      institution_name/banka, iban, description/açıklama
    """
    content = await _read_csv(file)
    svc = ImportService(session)
    preview = await svc.preview_accounts(content, current_user.tenant_id)
    return preview.dict()


@router.post("/accounts", status_code=201)
async def import_accounts(
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Import accounts from CSV. Skips duplicates by name. Admin only."""
    content = await _read_csv(file)
    svc = ImportService(session)
    result = await svc.import_accounts(
        content,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return result
