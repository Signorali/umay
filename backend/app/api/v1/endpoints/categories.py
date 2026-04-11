"""Category endpoints."""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission, get_user_group_ids
from app.models.user import User
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.common import PagedResponse, MessageResponse
from app.services.category_service import CategoryService
from app.utils.text_normalization import normalize_form_text

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=PagedResponse[CategoryResponse])
async def list_categories(
    current_user: Annotated[User, Depends(require_permission("categories", "view"))],
    group_ids: Annotated[List[uuid.UUID], Depends(get_user_group_ids)],
    session: AsyncSession = Depends(get_db),
    category_type: Optional[CategoryType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
):
    """List all categories in the current tenant."""
    svc = CategoryService(session)
    if category_type:
        items = await svc.list_by_type(category_type, current_user.tenant_id)
        total = len(items)
    else:
        items, total = await svc.list_by_tenant(
            current_user.tenant_id,
            offset=(page - 1) * page_size,
            limit=page_size,
            group_ids=group_ids or None,
        )
    return PagedResponse.build(
        items=[CategoryResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    current_user: Annotated[User, Depends(require_permission("categories", "create"))],
    session: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    # Normalize text fields
    normalized_body = body.model_copy(update={
        'name': normalize_form_text(body.name),
        'description': normalize_form_text(body.description) if body.description else None,
    })
    svc = CategoryService(session)
    category = await svc.create(
        tenant_id=current_user.tenant_id,
        data=normalized_body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return CategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("categories", "view"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CategoryService(session)
    return CategoryResponse.model_validate(
        await svc.get_by_id(category_id, current_user.tenant_id)
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    current_user: Annotated[User, Depends(require_permission("categories", "update"))],
    session: AsyncSession = Depends(get_db),
):
    # Normalize text fields
    update_dict = {}
    if body.name is not None:
        update_dict['name'] = normalize_form_text(body.name)
    if body.description is not None:
        update_dict['description'] = normalize_form_text(body.description)

    normalized_body = body.model_copy(update=update_dict) if update_dict else body
    svc = CategoryService(session)
    category = await svc.update(
        category_id=category_id,
        tenant_id=current_user.tenant_id,
        data=normalized_body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("categories", "delete"))],
    session: AsyncSession = Depends(get_db),
):
    svc = CategoryService(session)
    await svc.delete(
        category_id=category_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Category deleted successfully")
