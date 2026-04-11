"""OCR draft repository."""
import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocr_draft import OcrDraft, OcrDraftStatus


class OcrDraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> OcrDraft:
        obj = OcrDraft(tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, draft_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[OcrDraft]:
        q = select(OcrDraft).where(
            OcrDraft.id == draft_id,
            OcrDraft.tenant_id == tenant_id,
            OcrDraft.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[OcrDraft]:
        q = select(OcrDraft).where(
            OcrDraft.tenant_id == tenant_id,
            OcrDraft.is_deleted == False,
        )
        if status:
            q = q.where(OcrDraft.status == status)
        q = q.order_by(OcrDraft.created_at.desc()).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def update(self, draft: OcrDraft, data: dict) -> OcrDraft:
        for k, v in data.items():
            setattr(draft, k, v)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
