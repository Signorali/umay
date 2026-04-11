"""DocumentService — validated file upload, storage, and linkage management."""
import uuid
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.document import DocumentRepository
from app.services.audit_service import AuditService
from app.models.document import DocumentStatus

# Allowed MIME types
ALLOWED_MIME: set = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _storage_root() -> Path:
    p = Path(settings.STORAGE_PATH)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)
        self.audit = AuditService(db)

    async def upload(
        self,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        file: UploadFile,
        document_type: str = "OTHER",
        title: Optional[str] = None,
        notes: Optional[str] = None,
        linked_transaction_id: Optional[uuid.UUID] = None,
        linked_planned_payment_id: Optional[uuid.UUID] = None,
        linked_loan_id: Optional[uuid.UUID] = None,
        linked_credit_card_id: Optional[uuid.UUID] = None,
        linked_asset_id: Optional[uuid.UUID] = None,
    ):
        # Validate MIME
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type '{file.content_type}' is not allowed.",
            )

        # Create DB record (PENDING)
        doc = await self.repo.create(tenant_id, {
            "uploaded_by": actor_id,
            "document_type": document_type,
            "status": DocumentStatus.PENDING,
            "original_filename": file.filename or "upload",
            "mime_type": file.content_type,
            "title": title,
            "notes": notes,
            "linked_transaction_id": linked_transaction_id,
            "linked_planned_payment_id": linked_planned_payment_id,
            "linked_loan_id": linked_loan_id,
            "linked_credit_card_id": linked_credit_card_id,
            "linked_asset_id": linked_asset_id,
        })

        # Determine storage path: STORAGE_PATH/{tenant_id}/{doc.id}.ext
        suffix = Path(file.filename or "file").suffix or ""
        stored_name = f"{doc.id}{suffix}"
        tenant_dir = _storage_root() / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        dest = tenant_dir / stored_name

        try:
            content = await file.read()
            if len(content) > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                )
            dest.write_bytes(content)
            checksum = hashlib.sha256(content).hexdigest()
            size_bytes = len(content)
        except HTTPException:
            await self.repo.update(doc, {"status": DocumentStatus.FAILED})
            await self.db.commit()
            raise

        # Update record to STORED
        rel_path = f"{tenant_id}/{stored_name}"
        updated = await self.repo.update(doc, {
            "stored_filename": stored_name,
            "file_path": rel_path,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum,
            "status": DocumentStatus.STORED,
        })

        await self.audit.log(
            actor_id=actor_id, action="document.upload",
            module="documents", record_id=doc.id,
            new_state={"filename": file.filename, "size": size_bytes},
        )
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def get(self, doc_id: uuid.UUID, tenant_id: uuid.UUID):
        doc = await self.repo.get_by_id(doc_id, tenant_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        return doc

    async def get_file_path(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Path:
        doc = await self.get(doc_id, tenant_id)
        if not doc.file_path:
            raise HTTPException(status_code=404, detail="File not stored.")
        path = _storage_root() / doc.file_path
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk.")
        return path

    async def list(
        self,
        tenant_id: uuid.UUID,
        document_type: Optional[str] = None,
        linked_transaction_id: Optional[uuid.UUID] = None,
        linked_asset_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ):
        return await self.repo.list_by_tenant(
            tenant_id,
            document_type=document_type,
            linked_transaction_id=linked_transaction_id,
            linked_asset_id=linked_asset_id,
            skip=skip, limit=limit,
        )

    async def delete(self, doc_id: uuid.UUID, tenant_id: uuid.UUID, actor_id: uuid.UUID):
        doc = await self.get(doc_id, tenant_id)
        # Remove physical file
        if doc.file_path:
            path = _storage_root() / doc.file_path
            if path.exists():
                path.unlink()
        await self.repo.soft_delete(doc)
        await self.audit.log(
            actor_id=actor_id, action="document.delete",
            module="documents", record_id=doc_id,
        )
        await self.db.commit()
