"""Delete-request endpoints.

Regular users:
  POST   /delete-requests          — create a request
  GET    /delete-requests/mine     — list own requests

Tenant admins:
  GET    /delete-requests          — list all (filterable by status)
  POST   /delete-requests/{id}/approve
  POST   /delete-requests/{id}/reject
"""
import uuid
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin, require_permission
from app.models.user import User
from app.schemas.delete_request import DeleteRequestCreate, DeleteRequestResponse, DeleteRequestReview
from app.schemas.common import PagedResponse
from app.services.delete_request_service import DeleteRequestService

router = APIRouter(prefix="/delete-requests", tags=["delete-requests"])


@router.post("", response_model=DeleteRequestResponse, status_code=201)
async def create_delete_request(
    body: DeleteRequestCreate,
    current_user: Annotated[User, Depends(require_permission("delete_requests", "create"))],
    session: AsyncSession = Depends(get_db),
):
    """Any authenticated user with the permission can raise a delete request."""
    service = DeleteRequestService(session)
    req = await service.create_request(
        tenant_id=current_user.tenant_id,
        requested_by_user_id=current_user.id,
        target_table=body.target_table,
        target_id=body.target_id,
        target_label=body.target_label,
        reason=body.reason,
        actor_email=current_user.email,
    )
    await session.commit()
    return req


@router.get("/mine", response_model=PagedResponse[DeleteRequestResponse])
async def my_delete_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Return the current user's own delete requests."""
    service = DeleteRequestService(session)
    items, total = await service.list_my_requests(
        current_user.id, current_user.tenant_id, offset=offset, limit=limit
    )
    return PagedResponse.build(items=items, total=total, page=(offset // limit) + 1, page_size=limit)


@router.get("", response_model=PagedResponse[DeleteRequestResponse])
async def list_delete_requests(
    current_user: Annotated[User, Depends(require_permission("delete_requests", "review"))],
    session: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Admin: list all delete requests, optionally filtered by status."""
    service = DeleteRequestService(session)
    items, total = await service.list_pending(
        current_user.tenant_id, status=status, offset=offset, limit=limit
    )
    return PagedResponse.build(items=items, total=total, page=(offset // limit) + 1, page_size=limit)


@router.post("/{request_id}/approve", response_model=DeleteRequestResponse)
async def approve_delete_request(
    request_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("delete_requests", "review"))],
    session: AsyncSession = Depends(get_db),
):
    service = DeleteRequestService(session)
    req = await service.approve(
        request_id,
        tenant_id=current_user.tenant_id,
        reviewer_id=current_user.id,
        reviewer_email=current_user.email,
    )
    await session.commit()
    return req


@router.post("/{request_id}/reject", response_model=DeleteRequestResponse)
async def reject_delete_request(
    request_id: uuid.UUID,
    body: DeleteRequestReview,
    current_user: Annotated[User, Depends(require_permission("delete_requests", "review"))],
    session: AsyncSession = Depends(get_db),
):
    service = DeleteRequestService(session)
    req = await service.reject(
        request_id,
        tenant_id=current_user.tenant_id,
        reviewer_id=current_user.id,
        reject_reason=body.reject_reason,
        reviewer_email=current_user.email,
    )
    await session.commit()
    return req
