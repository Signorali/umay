"""OCR endpoints — submit document for extraction, review and accept/reject draft."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.ocr_service import OcrService

router = APIRouter(prefix="/ocr", tags=["ocr"])


class AcceptDraftRequest(BaseModel):
    override_amount: Optional[float] = None
    override_currency: Optional[str] = None
    override_date: Optional[str] = None
    override_description: Optional[str] = None
    override_category_id: Optional[uuid.UUID] = None
    override_account_id: Optional[uuid.UUID] = None
    override_transaction_type: Optional[str] = None


class RejectDraftRequest(BaseModel):
    review_notes: Optional[str] = None


@router.get("/drafts")
async def list_drafts(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = OcrService(db)
    return await svc.list_drafts(current_user.tenant_id, status=status, skip=skip, limit=limit)


@router.post("/documents/{document_id}/extract", status_code=202)
async def submit_for_extraction(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit a document for OCR/AI extraction. Returns a draft record."""
    svc = OcrService(db)
    return await svc.submit_for_extraction(document_id, current_user.tenant_id, current_user.id)


@router.get("/drafts/{draft_id}")
async def get_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = OcrService(db)
    return await svc.get_draft(draft_id, current_user.tenant_id)


@router.post("/drafts/{draft_id}/accept")
async def accept_draft(
    draft_id: uuid.UUID,
    body: AcceptDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Human confirms OCR extraction. Returns transaction data ready for posting.
    The actual transaction is NOT created here — caller must POST to /transactions.
    """
    svc = OcrService(db)
    overrides = {}
    if body.override_amount is not None:
        overrides["amount"] = body.override_amount
    if body.override_currency:
        overrides["currency"] = body.override_currency
    if body.override_description:
        overrides["description"] = body.override_description
    if body.override_category_id:
        overrides["category_id"] = body.override_category_id
    if body.override_account_id:
        overrides["source_account_id"] = body.override_account_id
    if body.override_transaction_type:
        overrides["transaction_type"] = body.override_transaction_type

    return await svc.accept_draft(
        draft_id, current_user.tenant_id, current_user.id,
        override_data=overrides if overrides else None,
    )


@router.post("/drafts/{draft_id}/reject")
async def reject_draft(
    draft_id: uuid.UUID,
    body: RejectDraftRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Human rejects the OCR draft."""
    svc = OcrService(db)
    return await svc.reject_draft(
        draft_id, current_user.tenant_id, current_user.id,
        review_notes=body.review_notes,
    )
