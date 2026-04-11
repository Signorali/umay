import uuid
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_tenant_admin
from app.schemas.user import UserCreate, UserUpdate, UserResponse, PasswordChange
from app.schemas.common import PagedResponse, MessageResponse
from app.services.user_service import UserService
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserPreferences(BaseModel):
    ui_theme: Optional[str] = None        # 'dark' | 'light'
    locale: Optional[str] = None          # 'tr' | 'en' etc.
    dashboard_layout: Optional[str] = None  # JSON string


@router.get("", response_model=PagedResponse[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = UserService(session)
    items, total = await service.list_by_tenant(
        current_user.tenant_id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PagedResponse.build(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    user = await service.create(
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.patch("/me/preferences", status_code=200)
async def update_preferences(
    body: UserPreferences,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Save UI preferences (theme, locale) for the current user to the database."""
    if body.ui_theme is not None:
        current_user.ui_theme = body.ui_theme
    if body.locale is not None:
        current_user.locale = body.locale
    if body.dashboard_layout is not None:
        current_user.dashboard_layout = body.dashboard_layout
    session.add(current_user)
    await session.commit()
    return {"ui_theme": current_user.ui_theme, "locale": current_user.locale, "dashboard_layout": current_user.dashboard_layout}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    return await service.get_by_id(user_id, current_user.tenant_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    user = await service.update(
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        data=body,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return user


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    body: PasswordChange,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    await service.change_password(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        data=body,
    )
    await session.commit()
    return MessageResponse(message="Password changed successfully")


class AdminPasswordReset(BaseModel):
    new_password: str


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def admin_reset_password(
    user_id: uuid.UUID,
    body: AdminPasswordReset,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Admin resets a user's password and forces them to change it on next login."""
    service = UserService(session)
    await service.admin_reset_password(
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        new_password=body.new_password,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Password reset successfully")


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    service = UserService(session)
    user = await service.deactivate(
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    if user_id == current_user.id:
        from app.core.exceptions import BusinessRuleError
        raise BusinessRuleError("Kendi hesabınızı silemezsiniz.")
    service = UserService(session)
    await service.delete(
        user_id=user_id,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    return MessageResponse(message="Kullanıcı silindi")
