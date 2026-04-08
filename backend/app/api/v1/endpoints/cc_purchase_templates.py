"""Credit card purchase template endpoints."""
import uuid
from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import require_permission
from app.models.user import User
from app.models.cc_purchase_template import CcPurchaseTemplate
from pydantic import BaseModel

router = APIRouter(prefix="/cc-purchase-templates", tags=["cc-purchase-templates"])


class CcTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    installment_count: int = 1
    currency: str = "TRY"
    category_id: Optional[uuid.UUID] = None


class CcTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    installment_count: int
    currency: str
    category_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


@router.get("", response_model=List[CcTemplateResponse])
async def list_templates(
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CcPurchaseTemplate)
        .where(
            CcPurchaseTemplate.tenant_id == current_user.tenant_id,
            CcPurchaseTemplate.is_deleted == False,
        )
        .order_by(CcPurchaseTemplate.name)
    )
    return [CcTemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=CcTemplateResponse, status_code=201)
async def create_template(
    body: CcTemplateCreate,
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    tmpl = CcPurchaseTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
        installment_count=body.installment_count,
        currency=body.currency,
        category_id=body.category_id,
    )
    session.add(tmpl)
    await session.commit()
    await session.refresh(tmpl)
    return CcTemplateResponse.model_validate(tmpl)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("transactions", "view"))],
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CcPurchaseTemplate).where(
            CcPurchaseTemplate.id == template_id,
            CcPurchaseTemplate.tenant_id == current_user.tenant_id,
            CcPurchaseTemplate.is_deleted == False,
        )
    )
    tmpl = result.scalar_one_or_none()
    if tmpl:
        tmpl.is_deleted = True
        await session.commit()
