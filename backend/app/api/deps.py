import uuid
from typing import Annotated, List, Optional, Set
from fastapi import Cookie, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
    umay_token: Annotated[Optional[str], Cookie()] = None,
) -> User:
    # Accept token from Authorization: Bearer header OR httpOnly cookie
    raw_token = credentials.credentials if credentials else umay_token
    if not raw_token:
        raise UnauthorizedError("Missing authentication token")

    payload = decode_token(raw_token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")

    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (KeyError, ValueError):
        raise UnauthorizedError("Malformed token")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user or user.tenant_id != tenant_id or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser access required")
    return current_user


async def get_current_tenant_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not (current_user.is_tenant_admin or current_user.is_superuser):
        raise ForbiddenError("Tenant admin access required")
    return current_user


async def get_user_group_ids(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> List[uuid.UUID]:
    if current_user.is_superuser or current_user.is_tenant_admin:
        return []  # empty = no filter (admins see all)
    from app.repositories.group import GroupRepository
    repo = GroupRepository(session)
    return await repo.get_user_group_ids(current_user.id, current_user.tenant_id)


async def get_user_permissions(user: User, session: AsyncSession) -> Set[str]:
    """
    Return the set of 'module:action' strings the user holds.
    Admins/superusers get {'*'} (wildcard = all permissions).
    """
    if user.is_superuser or user.is_tenant_admin:
        return {"*"}

    if not user.role_id:
        return set()

    from app.models.permission import RolePermission, Permission
    result = await session.execute(
        select(Permission.module, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id, RolePermission.is_deleted == False)
    )
    return {f"{row.module}:{row.action}" for row in result}


def require_permission(module: str, action: str):
    """
    Dependency factory — use as:
        current_user: User = Depends(require_permission("transactions", "delete"))

    Admins and superusers bypass all permission checks.
    Regular users need the specific module:action in their role's permissions.
    """
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        if current_user.is_superuser or current_user.is_tenant_admin:
            return current_user

        perms = await get_user_permissions(current_user, session)
        if "*" not in perms and f"{module}:{action}" not in perms:
            raise ForbiddenError(
                f"Bu işlem için '{module}.{action}' yetkisi gereklidir."
            )
        return current_user

    return _check


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def require_license_feature(feature: str):
    """
    Dependency factory — blocks the endpoint if the tenant's license
    does not include the given feature.

    Superusers bypass all license checks.

    Usage:
        @router.get("/reports")
        async def get_reports(
            _: User = Depends(require_license_feature("reports")),
        ): ...
    """
    async def _check(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> User:
        if current_user.is_superuser:
            return current_user

        from app.core.redis_client import get_redis
        from app.services.license_service import LicenseService
        from app.core.exceptions import ForbiddenError as _ForbiddenError

        redis = await get_redis()
        svc = LicenseService(session=session, redis=redis)
        allowed = await svc.check_feature(current_user.tenant_id, feature)
        if not allowed:
            raise _ForbiddenError(
                f"Bu özellik mevcut lisans planınızda bulunmuyor: '{feature}'. "
                "Lütfen lisansınızı yükseltin."
            )
        return current_user

    return _check
