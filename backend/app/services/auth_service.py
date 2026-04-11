import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.audit_service import AuditService
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import UnauthorizedError, BusinessRuleError

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserRepository(session)
        self.audit = AuditService(session)

    async def login(
        self,
        tenant_id: uuid.UUID,
        data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = await self.repo.get_by_email(data.email, tenant_id)

        if not user:
            raise UnauthorizedError("Invalid credentials")

        if not user.is_active:
            raise UnauthorizedError("Account is inactive")

        # Brute force protection
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise BusinessRuleError(
                f"Account locked until {user.locked_until.isoformat()}. Try again later."
            )

        if not verify_password(data.password, user.hashed_password):
            lock_until = None
            if user.failed_login_count + 1 >= MAX_FAILED_ATTEMPTS:
                lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            await self.repo.increment_failed_login(user, lock_until=lock_until)
            await self.audit.log(
                action="LOGIN_FAILED",
                module="auth",
                tenant_id=tenant_id,
                actor_email=data.email,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise UnauthorizedError("Invalid credentials")

        await self.repo.record_login(user)
        await self.audit.log(
            action="LOGIN",
            module="auth",
            tenant_id=tenant_id,
            actor_id=user.id,
            actor_email=user.email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        extra_claims = {
            "tenant_id": str(tenant_id),
            "email": user.email,
            "is_superuser": user.is_superuser,
            "is_tenant_admin": user.is_tenant_admin,
        }
        access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str, tenant_id: uuid.UUID) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid or expired refresh token")

        user_id = uuid.UUID(payload["sub"])
        user = await self.repo.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id or not user.is_active:
            raise UnauthorizedError("Invalid refresh token")

        extra_claims = {
            "tenant_id": str(tenant_id),
            "email": user.email,
            "is_superuser": user.is_superuser,
            "is_tenant_admin": user.is_tenant_admin,
        }
        new_access_token = create_access_token(subject=user.id, extra_claims=extra_claims)
        new_refresh_token = create_refresh_token(subject=user.id)
        return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)
