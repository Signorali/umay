"""Document repository."""
import uuid
import hashlib
from pathlib import Path
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Document:
        obj = Document(tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Document]:
        q = select(Document).where(
            Document.id == doc_id,
            Document.tenant_id == tenant_id,
            Document.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        document_type: Optional[str] = None,
        linked_transaction_id: Optional[uuid.UUID] = None,
        linked_asset_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Document]:
        q = select(Document).where(
            Document.tenant_id == tenant_id,
            Document.is_deleted == False,
            Document.status != DocumentStatus.DELETED,
        )
        if document_type:
            q = q.where(Document.document_type == document_type)
        if linked_transaction_id:
            q = q.where(Document.linked_transaction_id == linked_transaction_id)
        if linked_asset_id:
            q = q.where(Document.linked_asset_id == linked_asset_id)
        q = q.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def update(self, doc: Document, data: dict) -> Document:
        for k, v in data.items():
            setattr(doc, k, v)
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def soft_delete(self, doc: Document) -> None:
        doc.is_deleted = True
        doc.status = DocumentStatus.DELETED
        await self.db.flush()
