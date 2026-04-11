import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse, GroupMemberAdd, GroupMemberRemove
from app.schemas.common import PagedResponse, MessageResponse
from app.services.group_service import GroupService
from app.models.user import User

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=PagedResponse[GroupResponse])
async def list_groups(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = GroupService(session)
    if current_user.is_superuser or current_user.is_tenant_admin:
        items, total = await service.list_by_tenant(
            current_user.tenant_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
    else:
        items, total = await service.list_by_user(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
    return PagedResponse.build(
        items=[GroupResponse.model_validate(g) for g in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: GroupCreate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    group = await service.create(
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return GroupResponse.model_validate(group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    return GroupResponse.model_validate(
        await service.get_accessible(
            group_id=group_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            is_admin=current_user.is_tenant_admin or current_user.is_superuser,
        )
    )


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    group = await service.update(
        group_id=group_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    await service.delete(
        group_id=group_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Group deleted successfully")


@router.post("/{group_id}/members", response_model=MessageResponse, status_code=201)
async def add_member(
    group_id: uuid.UUID,
    body: GroupMemberAdd,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    await service.add_member(
        group_id=group_id,
        tenant_id=current_user.tenant_id,
        user_id=body.user_id,
    )
    await session.commit()
    return MessageResponse(message="Member added to group")


@router.delete("/{group_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = GroupService(session)
    await service.remove_member(
        group_id=group_id,
        tenant_id=current_user.tenant_id,
        user_id=user_id,
    )
    await session.commit()
    return MessageResponse(message="Member removed from group")
