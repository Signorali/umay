"""Documents endpoints — upload, download, and link management."""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
async def list_documents(
    document_type: Optional[str] = Query(None),
    linked_transaction_id: Optional[uuid.UUID] = Query(None),
    linked_asset_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("documents", "view")),
):
    svc = DocumentService(db)
    return await svc.list(
        current_user.tenant_id,
        document_type=document_type,
        linked_transaction_id=linked_transaction_id,
        linked_asset_id=linked_asset_id,
        skip=skip, limit=limit,
    )


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("OTHER"),
    title: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    linked_transaction_id: Optional[uuid.UUID] = Form(None),
    linked_planned_payment_id: Optional[uuid.UUID] = Form(None),
    linked_loan_id: Optional[uuid.UUID] = Form(None),
    linked_credit_card_id: Optional[uuid.UUID] = Form(None),
    linked_asset_id: Optional[uuid.UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("documents", "create")),
):
    svc = DocumentService(db)
    return await svc.upload(
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        file=file,
        document_type=document_type,
        title=title,
        notes=notes,
        linked_transaction_id=linked_transaction_id,
        linked_planned_payment_id=linked_planned_payment_id,
        linked_loan_id=linked_loan_id,
        linked_credit_card_id=linked_credit_card_id,
        linked_asset_id=linked_asset_id,
    )


@router.get("/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("documents", "view")),
):
    svc = DocumentService(db)
    return await svc.get(document_id, current_user.tenant_id)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("documents", "view")),
):
    svc = DocumentService(db)
    path = await svc.get_file_path(document_id, current_user.tenant_id)
    doc = await svc.get(document_id, current_user.tenant_id)
    return FileResponse(
        path=str(path),
        media_type=doc.mime_type or "application/octet-stream",
        filename=doc.original_filename,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("documents", "delete")),
):
    svc = DocumentService(db)
    await svc.delete(document_id, current_user.tenant_id, current_user.id)
