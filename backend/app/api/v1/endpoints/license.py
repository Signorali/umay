"""
license.py — License management endpoints

GET  /license/status          — Current tenant's license status
POST /license/activate        — Activate a new license key (tenant admin)
DELETE /license               — Deactivate license (superuser only)

Superuser endpoints:
GET  /license/admin/{tenant_id}/status  — Check any tenant's license
"""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_admin, get_current_superuser, get_current_user
from app.core.database import get_db
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.license_crypto import (
    LicenseError,
    LicenseExpiredError,
    LicenseTamperedError,
    LicenseTenantMismatchError,
)
from app.core.redis_client import get_redis
from app.models.user import User
from app.schemas.license import (
    LicenseActivateRequest,
    LicenseActivateResponse,
    LicenseStatusResponse,
)
from app.services.license_service import LicenseService

router = APIRouter(prefix="/license", tags=["license"])


def _build_service(session: AsyncSession, redis=None) -> LicenseService:
    return LicenseService(session=session, redis=redis)


# ---------------------------------------------------------------------------
# Tenant endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=LicenseStatusResponse)
async def get_license_status(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """Return the current license status for the authenticated tenant."""
    redis = await get_redis()
    svc = _build_service(session, redis)
    status = await svc.get_status_dict(current_user.tenant_id)
    return LicenseStatusResponse(**status)


@router.post("/activate", response_model=LicenseActivateResponse)
async def activate_license(
    body: LicenseActivateRequest,
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """
    Activate a license key for the current tenant.
    Requires tenant admin or superuser role.
    """
    redis = await get_redis()
    svc = _build_service(session, redis)

    try:
        payload = await svc.activate(current_user.tenant_id, body.license_key.strip())
    except LicenseTamperedError as exc:
        raise BadRequestError(f"Geçersiz lisans anahtarı: {exc}")
    except LicenseExpiredError as exc:
        raise BadRequestError(f"Lisans süresi dolmuş: {exc}")
    except LicenseTenantMismatchError as exc:
        raise BadRequestError(f"Lisans bu tenant'a ait değil: {exc}")
    except LicenseError as exc:
        raise BadRequestError(f"Lisans hatası: {exc}")

    # update.sh için lisans anahtarını dosyaya kaydet
    try:
        storage_path = os.environ.get("STORAGE_PATH", "/app/storage")
        license_file = os.path.join(storage_path, "license.key")
        with open(license_file, "w") as f:
            f.write(body.license_key.strip())
    except Exception:
        pass  # Dosya yazma hatası lisansı geçersiz kılmasın

    status = await svc.get_status_dict(current_user.tenant_id)
    return LicenseActivateResponse(
        success=True,
        message=f"Lisans başarıyla aktive edildi — Plan: {payload.plan.value.upper()}",
        status=LicenseStatusResponse(**status),
    )


@router.delete("", status_code=204)
async def deactivate_license(
    current_user: Annotated[User, Depends(get_current_tenant_admin)],
    session: AsyncSession = Depends(get_db),
):
    """Deactivate the current tenant's license (reverts to trial mode)."""
    redis = await get_redis()
    svc = _build_service(session, redis)
    await svc.deactivate(current_user.tenant_id)


# ---------------------------------------------------------------------------
# Superuser admin endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/{tenant_id}/status", response_model=LicenseStatusResponse)
async def admin_get_tenant_license(
    tenant_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    """[Superuser] Check any tenant's license status."""
    redis = await get_redis()
    svc = _build_service(session, redis)
    status = await svc.get_status_dict(tenant_id)
    return LicenseStatusResponse(**status)


@router.post("/admin/{tenant_id}/deactivate", status_code=204)
async def admin_deactivate_tenant_license(
    tenant_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    """[Superuser] Deactivate a specific tenant's license."""
    redis = await get_redis()
    svc = _build_service(session, redis)
    await svc.deactivate(tenant_id)
