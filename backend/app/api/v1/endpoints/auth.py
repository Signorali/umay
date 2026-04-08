import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user, get_client_ip
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.models.user import User
from app.core.rate_limit import limiter
from app.core.config import settings

router = APIRouter()

# Cookie is secure only when running over HTTPS (i.e. not localhost dev)
_SECURE = not settings.DEBUG if hasattr(settings, 'DEBUG') else False


def _set_auth_cookies(response: Response, access_token: str, tenant_id: str) -> None:
    """Set httpOnly auth cookie + readable tenant cookie."""
    response.set_cookie(
        key="umay_token",
        value=access_token,
        httponly=True,
        secure=_SECURE,
        samesite="lax",
        max_age=60 * 60,       # 1 hour (matches JWT expiry)
        path="/",
    )
    # tenant_id is NOT secret — JS needs to read it for the login form
    response.set_cookie(
        key="umay_tenant_id",
        value=str(tenant_id),
        httponly=False,
        secure=_SECURE,
        samesite="lax",
        max_age=365 * 24 * 60 * 60,  # 1 year
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        "umay_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=_SECURE,
    )
    response.delete_cookie(
        "umay_tenant_id",
        path="/",
        httponly=False,
        samesite="lax",
        secure=_SECURE,
    )


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    x_tenant_id: Annotated[uuid.UUID, Header()],
    session: AsyncSession = Depends(get_db),
):
    """Login with email/password. Sets httpOnly auth cookie in addition to returning tokens."""
    service = AuthService(session)
    result = await service.login(
        tenant_id=x_tenant_id,
        data=body,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    _set_auth_cookies(response, result.access_token, str(x_tenant_id))
    return result


@router.post("/auth/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    response: Response,
    x_tenant_id: Annotated[uuid.UUID, Header()],
    session: AsyncSession = Depends(get_db),
):
    """Obtain a new access token. Refreshes the auth cookie too."""
    service = AuthService(session)
    result = await service.refresh(body.refresh_token, tenant_id=x_tenant_id)
    _set_auth_cookies(response, result.access_token, str(x_tenant_id))
    return result


@router.get("/auth/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user with permissions list."""
    from app.api.deps import get_user_permissions
    perms = await get_user_permissions(current_user, session)
    # Attach permissions to the response (not a DB field — computed on the fly)
    user_dict = {
        "id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "is_tenant_admin": current_user.is_tenant_admin,
        "role_id": current_user.role_id,
        "last_login_at": current_user.last_login_at,
        "locale": current_user.locale,
        "timezone": current_user.timezone,
        "ui_theme": current_user.ui_theme,
        "must_change_password": current_user.must_change_password,
        "permissions": sorted(perms),
        "created_at": current_user.created_at,
    }
    return UserResponse(**user_dict)


@router.post("/auth/logout", status_code=200)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Logout: clear auth cookie server-side + audit log."""
    service = AuthService(session)
    await service.audit.log(
        action="LOGOUT",
        module="auth",
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
    )
    await session.commit()
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
