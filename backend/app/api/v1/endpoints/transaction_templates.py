"""Transaction template endpoints."""
import uuid
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import require_permission
from app.models.user import User
from app.models.transaction_template import TransactionTemplate
from pydantic import BaseModel

router = APIRouter(prefix="/transaction-templates", tags=["transaction-templates"])


class TemplateCreate(BaseModel):
    name: str
    transaction_type: str
    currency: str = "TRY"
    source_account_id: Optional[uuid.UUID] = None
    target_account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    transaction_type: str
    currency: str
    source_account_id: Optional[uuid.UUID]
    target_account_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    description: Optional[str]

    model_config = {"from_attributes": True}


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(TransactionTemplate)
        .where(
            TransactionTemplate.tenant_id == current_user.tenant_id,
            TransactionTemplate.is_deleted == False,
        )
        .order_by(TransactionTemplate.name)
    )
    return [TemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    tmpl = TransactionTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        transaction_type=body.transaction_type,
        currency=body.currency,
        source_account_id=body.source_account_id,
        target_account_id=body.target_account_id,
        category_id=body.category_id,
        description=body.description,
    )
    session.add(tmpl)
    await session.commit()
    await session.refresh(tmpl)
    return TemplateResponse.model_validate(tmpl)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(TransactionTemplate).where(
            TransactionTemplate.id == template_id,
            TransactionTemplate.tenant_id == current_user.tenant_id,
            TransactionTemplate.is_deleted == False,
        )
    )
    tmpl = result.scalar_one_or_none()
    if tmpl:
        tmpl.is_deleted = True
        await session.commit()
