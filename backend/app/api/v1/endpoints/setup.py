"""
Setup Wizard endpoint.

Rules:
- GET /setup/status    — public, no auth. Returns whether system is initialized.
- POST /setup/init     — public, no auth. Only works if system is NOT yet initialized.
  After success, this endpoint CANNOT be called again (idempotent guard).
- Once setup is complete, any further POST /setup/init returns 409.

First-run flow creates:
  1. First tenant
  2. System permissions seeded
  3. Admin role (system role)
  4. Default group
  5. First admin user (is_superuser + is_tenant_admin, member of default group)
  6. Tenant marked as setup_complete

Admin credentials come from:
  - request body (explicit)
  OR
  - FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD env vars (fallback)
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password
from app.core.exceptions import ConflictError, BusinessRuleError
from app.models.tenant import Tenant
from app.models.user import User, UserGroup
from app.models.role import Role
from app.models.group import Group
from app.services.role_service import RoleService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupStatusResponse(BaseModel):
    initialized: bool
    version: str
    environment: str
    tenant_id: Optional[str] = None


class SetupInitRequest(BaseModel):
    tenant_name: str = "Default"
    tenant_slug: str = "default"
    base_currency: str = "TRY"
    timezone: str = "Europe/Istanbul"
    locale: str = "tr-TR"
    admin_email: Optional[EmailStr] = None
    admin_password: Optional[str] = None
    admin_full_name: str = "System Administrator"
    default_group_name: str = "Default"


class SetupInitResponse(BaseModel):
    message: str
    tenant_id: str
    admin_email: str
    group_id: str


async def _is_initialized(session: AsyncSession) -> bool:
    result = await session.execute(
        select(func.count(Tenant.id)).where(
            Tenant.is_setup_complete == True,
            Tenant.is_deleted == False,
        )
    )
    count = result.scalar_one()
    return count > 0


async def _get_tenant_id(session: AsyncSession) -> Optional[str]:
    result = await session.execute(
        select(Tenant.id).where(
            Tenant.is_setup_complete == True,
            Tenant.is_deleted == False,
        ).limit(1)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else None


@router.get("/precheck")
async def setup_precheck(session: AsyncSession = Depends(get_db)):
    import os
    from datetime import datetime, timezone

    checks = []

    try:
        await session.execute(select(func.count(Tenant.id)))
        checks.append({"name": "database_connectivity", "status": "ok"})
    except Exception as exc:
        checks.append({"name": "database_connectivity", "status": "error", "detail": str(exc)[:80]})

    storage_path = settings.STORAGE_PATH
    try:
        os.makedirs(storage_path, exist_ok=True)
        test_file = os.path.join(storage_path, ".write_check")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        checks.append({"name": "writable_storage", "status": "ok", "path": storage_path})
    except Exception as exc:
        checks.append({"name": "writable_storage", "status": "error", "path": storage_path, "detail": str(exc)[:80]})

    backup_path = settings.BACKUP_PATH
    try:
        os.makedirs(backup_path, exist_ok=True)
        accessible = os.access(backup_path, os.W_OK)
        checks.append({
            "name": "backup_path_readiness",
            "status": "ok" if accessible else "error",
            "path": backup_path,
        })
    except Exception as exc:
        checks.append({"name": "backup_path_readiness", "status": "error", "detail": str(exc)[:80]})

    secrets_ok = bool(settings.APP_SECRET_KEY and len(settings.APP_SECRET_KEY) >= 20)
    jwt_ok = bool(settings.JWT_SECRET_KEY and len(settings.JWT_SECRET_KEY) >= 20)
    checks.append({
        "name": "required_secrets",
        "status": "ok" if (secrets_ok and jwt_ok) else "error",
        "app_secret": "set" if secrets_ok else "missing_or_weak",
        "jwt_secret": "set" if jwt_ok else "missing_or_weak",
    })

    try:
        from app.core.redis_client import get_redis
        r = await get_redis()
        await r.ping()
        checks.append({"name": "redis_connectivity", "status": "ok"})
    except Exception as exc:
        checks.append({"name": "redis_connectivity", "status": "warning", "detail": str(exc)[:80]})

    try:
        now = datetime.now(timezone.utc)
        checks.append({"name": "time_sync", "status": "ok", "utc_now": now.isoformat()})
    except Exception as exc:
        checks.append({"name": "time_sync", "status": "warning", "detail": str(exc)[:80]})

    env_valid = settings.APP_ENV in ("development", "production", "staging")
    checks.append({
        "name": "environment_config",
        "status": "ok" if env_valid else "warning",
        "environment": settings.APP_ENV,
    })

    all_pass = all(c["status"] in ("ok", "warning") for c in checks)
    critical_pass = all(
        c["status"] == "ok"
        for c in checks
        if c["name"] in ("database_connectivity", "writable_storage", "required_secrets")
    )

    return {
        "ready_to_install": critical_pass,
        "all_passed": all_pass,
        "checks": checks,
    }


@router.get("/status", response_model=SetupStatusResponse)
async def setup_status(session: AsyncSession = Depends(get_db)):
    initialized = await _is_initialized(session)
    tenant_id = await _get_tenant_id(session) if initialized else None
    return SetupStatusResponse(
        initialized=initialized,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        tenant_id=tenant_id,
    )


@router.post("/init", response_model=SetupInitResponse, status_code=201)
async def setup_init(
    body: SetupInitRequest,
    session: AsyncSession = Depends(get_db),
):
    if await _is_initialized(session):
        raise ConflictError("System is already initialized. Setup cannot be run again.")

    admin_email = body.admin_email or settings.FIRST_ADMIN_EMAIL
    admin_password = body.admin_password or settings.FIRST_ADMIN_PASSWORD

    if not admin_email or not admin_password:
        raise BusinessRuleError(
            "Admin email and password are required. "
            "Provide them in the request body or set FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD in the environment."
        )

    if len(admin_password) < 8:
        raise BusinessRuleError("Admin password must be at least 8 characters.")

    # --- 1. Create tenant ---
    TRIAL_DAYS = 30
    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_slug,
        base_currency=body.base_currency,
        timezone=body.timezone,
        locale=body.locale,
        is_active=True,
        is_setup_complete=False,
        trial_expires_at=datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS),
    )
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)

    # --- 2. Seed system permissions ---
    role_service = RoleService(session)
    await role_service.seed_permissions()

    # --- 3. Create admin role ---
    admin_role = Role(
        tenant_id=tenant.id,
        name="Administrator",
        description="Full-access system role. Cannot be deleted.",
        is_system=True,
        is_active=True,
    )
    session.add(admin_role)
    await session.flush()
    await session.refresh(admin_role)

    # --- 4. Create default group ---
    default_group = Group(
        tenant_id=tenant.id,
        name=body.default_group_name or "Default",
        description="Default group created during system setup.",
        is_active=True,
    )
    session.add(default_group)
    await session.flush()
    await session.refresh(default_group)

    # --- 5. Create first admin user ---
    admin_user = User(
        tenant_id=tenant.id,
        email=admin_email,
        hashed_password=hash_password(admin_password),
        full_name=body.admin_full_name,
        is_active=True,
        is_superuser=True,
        is_tenant_admin=True,
        role_id=admin_role.id,
        locale=body.locale,
        timezone=body.timezone,
    )
    session.add(admin_user)
    await session.flush()
    await session.refresh(admin_user)

    # --- 6. Add admin to default group ---
    user_group = UserGroup(
        user_id=admin_user.id,
        group_id=default_group.id,
    )
    session.add(user_group)
    await session.flush()

    # --- 7. Mark tenant as setup complete ---
    tenant.is_setup_complete = True
    await session.flush()

    # --- 8. Audit log ---
    audit = AuditService(session)
    await audit.log(
        action="SYSTEM_SETUP_COMPLETE",
        module="setup",
        tenant_id=tenant.id,
        actor_email=admin_email,
        after={
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "admin_email": admin_email,
            "default_group": body.default_group_name,
        },
    )

    await session.commit()

    return SetupInitResponse(
        message="System initialized successfully. You can now log in.",
        tenant_id=str(tenant.id),
        admin_email=admin_email,
        group_id=str(default_group.id),
    )
