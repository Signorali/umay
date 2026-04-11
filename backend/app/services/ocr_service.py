"""
OcrService — structured field extraction from documents.

RULE (cloud.md): AI can only create DRAFTS or suggestions.
                 Never post a final accounting entry without human confirmation.
"""
import uuid
import re
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ocr_draft import OcrDraftRepository
from app.repositories.document import DocumentRepository
from app.services.audit_service import AuditService
from app.models.ocr_draft import OcrDraftStatus


# ---------------------------------------------------------------------------
# Mock extractor — replace with real OCR engine (Tesseract / cloud Vision API)
# ---------------------------------------------------------------------------

def _mock_extract(filename: str, mime_type: Optional[str]) -> dict:
    """
    Returns a plausible-looking extraction result for dev/demo mode.
    In production, replace this with a real OCR call.
    """
    return {
        "suggested_amount": Decimal("150.00"),
        "suggested_currency": "TRY",
        "suggested_date": date.today(),
        "suggested_description": f"Mock extraction from {filename}",
        "suggested_transaction_type": "EXPENSE",
        "raw_extraction": {
            "engine": "mock",
            "text": f"[Mock OCR output for {filename}]",
            "fields": {"total": "150,00 TL", "date": str(date.today())},
        },
        "confidence_score": Decimal("0.72"),
    }


class OcrService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OcrDraftRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.audit = AuditService(db)

    async def submit_for_extraction(
        self,
        doc_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> "OcrDraft":
        """
        Create an OCR draft record and run extraction (mock or real).
        On success: status → READY
        On failure:  status → FAILED
        """
        doc = await self.doc_repo.get_by_id(doc_id, tenant_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        if doc.ocr_extracted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This document has already been submitted for OCR.",
            )

        draft = await self.repo.create(tenant_id, {
            "document_id": doc_id,
            "created_by": actor_id,
            "status": OcrDraftStatus.PROCESSING,
        })

        try:
            extracted = _mock_extract(doc.original_filename, doc.mime_type)
            draft = await self.repo.update(draft, {
                **extracted,
                "status": OcrDraftStatus.READY,
            })
            # Mark document as OCR-processed
            await self.doc_repo.update(doc, {
                "ocr_extracted": True,
                "ocr_draft_id": draft.id,
            })
        except Exception as exc:
            draft = await self.repo.update(draft, {
                "status": OcrDraftStatus.FAILED,
                "processing_error": str(exc),
            })

        await self.audit.log(
            actor_id=actor_id, action="ocr.submit",
            module="ocr", record_id=str(draft.id),
            after={"status": draft.status, "document_id": str(doc_id)},
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def accept_draft(
        self,
        draft_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        override_data: Optional[dict] = None,
    ) -> dict:
        """
        Human accepts the draft and provides final field values.
        Returns a dict ready to be passed to TransactionService.create_transaction.
        Does NOT call TransactionService here — the endpoint layer does that.
        """
        draft = await self._get_or_404(draft_id, tenant_id)
        if draft.status not in (OcrDraftStatus.READY,):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Draft status is '{draft.status}' — only READY drafts can be accepted.",
            )

        # Merge overrides with suggestions
        tx_data = {
            "transaction_type": draft.suggested_transaction_type or "EXPENSE",
            "amount": draft.suggested_amount,
            "currency": draft.suggested_currency or "TRY",
            "transaction_date": draft.suggested_date or date.today(),
            "description": draft.suggested_description,
            "category_id": draft.suggested_category_id,
            "source_account_id": draft.suggested_account_id,
        }
        if override_data:
            tx_data.update(override_data)

        await self.repo.update(draft, {
            "status": OcrDraftStatus.ACCEPTED,
            "reviewed_by": actor_id,
            "reviewed_at": datetime.now(timezone.utc),
        })
        await self.audit.log(
            actor_id=actor_id, action="ocr.accept",
            module="ocr", record_id=str(draft_id),
        )
        await self.db.commit()
        return tx_data

    async def reject_draft(
        self,
        draft_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        review_notes: Optional[str] = None,
    ):
        draft = await self._get_or_404(draft_id, tenant_id)
        await self.repo.update(draft, {
            "status": OcrDraftStatus.REJECTED,
            "reviewed_by": actor_id,
            "reviewed_at": datetime.now(timezone.utc),
            "review_notes": review_notes,
        })
        await self.audit.log(
            actor_id=actor_id, action="ocr.reject",
            module="ocr", record_id=str(draft_id),
        )
        await self.db.commit()
        return draft

    async def list_drafts(
        self, tenant_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0, limit: int = 50,
    ):
        return await self.repo.list_by_tenant(tenant_id, status=status, skip=skip, limit=limit)

    async def get_draft(self, draft_id: uuid.UUID, tenant_id: uuid.UUID):
        return await self._get_or_404(draft_id, tenant_id)

    async def _get_or_404(self, draft_id: uuid.UUID, tenant_id: uuid.UUID):
        d = await self.repo.get_by_id(draft_id, tenant_id)
        if not d:
            raise HTTPException(status_code=404, detail="OCR draft not found.")
        return d

    async def process_draft(self, draft_id: uuid.UUID) -> dict:
        """
        Worker-callable method: process an OcrDraft that already exists (status=PENDING).
        Transitions: PENDING → PROCESSING → READY | FAILED
        Does NOT create a transaction — only fills suggested_* fields.
        """
        from sqlalchemy import select as sa_select
        from app.models.ocr_draft import OcrDraft

        q = sa_select(OcrDraft).where(
            OcrDraft.id == draft_id,
            OcrDraft.is_deleted == False,
        )
        result = await self.db.execute(q)
        draft = result.scalar_one_or_none()
        if not draft:
            return {"status": "not_found", "draft_id": str(draft_id)}

        if draft.status not in (OcrDraftStatus.PENDING, OcrDraftStatus.PROCESSING):
            return {"status": draft.status, "draft_id": str(draft_id), "skipped": True}

        # Mark as processing
        await self.repo.update(draft, {"status": OcrDraftStatus.PROCESSING})

        try:
            # Get linked document info
            doc = None
            if draft.document_id:
                doc = await self.doc_repo.get_by_id(draft.document_id, draft.tenant_id)

            filename = doc.original_filename if doc else "unknown.pdf"
            mime_type = doc.mime_type if doc else None
            extracted = _mock_extract(filename, mime_type)

            await self.repo.update(draft, {
                **extracted,
                "status": OcrDraftStatus.READY,
            })
            if doc:
                await self.doc_repo.update(doc, {
                    "ocr_extracted": True,
                    "ocr_draft_id": draft.id,
                })

            return {
                "status": "ready",
                "draft_id": str(draft_id),
                "confidence": float(extracted.get("confidence_score", 0)),
            }
        except Exception as exc:
            await self.repo.update(draft, {
                "status": OcrDraftStatus.FAILED,
                "processing_error": str(exc),
            })
            return {"status": "failed", "draft_id": str(draft_id), "error": str(exc)}
