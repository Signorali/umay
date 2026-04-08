"""System management endpoints — flags, maintenance, health details, version."""
import os
import uuid
import httpx
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, engine, Base
from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.config import settings
from app.services.maintenance_service import MaintenanceService
from app.services.restore_validator import RestoreValidator
import app.models  # Ensure metadata is populated

router = APIRouter(prefix="/system", tags=["system"])

UPDATE_SERVER_URL = os.environ.get("UPDATE_SERVER_URL", "https://koken.myqnapcloud.com/update")


def _current_version() -> str:
    return os.environ.get("APP_VERSION", "dev")


# ------------------------------------------------------------------ #
# Version / Update check
# ------------------------------------------------------------------ #

@router.get("/version")
async def get_version(current_user=Depends(get_current_user)):
    """Kurulu sürümü döner."""
    return {"version": _current_version()}


class VersionCheckRequest(BaseModel):
    license_key: str


@router.post("/version/check")
async def check_for_update(
    body: VersionCheckRequest,
    current_user=Depends(get_current_user),
):
    """Update server'a lisans göndererek güncel sürüm bilgisini alır."""
    if not (current_user.is_superuser or current_user.is_tenant_admin):
        raise HTTPException(status_code=403, detail="Yalnızca yöneticiler güncelleme kontrolü yapabilir")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{UPDATE_SERVER_URL}/check",
                json={"license_key": body.license_key, "current_version": _current_version()},
            )
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="Lisans geçersiz veya süresi dolmuş")
            resp.raise_for_status()
            data = resp.json()
        data.pop("registry", None)  # Registry credentials'ı frontend'e gönderme
        return data
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Update server'a ulaşılamadı")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Update server bağlantı hatası")


class MaintenanceRequest(BaseModel):
    reason: Optional[str] = None


class ScheduleWindowRequest(BaseModel):
    label: str
    reason: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime


# ------------------------------------------------------------------ #
# System flags
# ------------------------------------------------------------------ #

@router.get("/flags")
async def get_flags(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.get_all_flags()


@router.put("/flags/{flag_key}")
async def set_flag(
    flag_key: str,
    value: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    flag = await svc.set_flag(flag_key, value, current_user.id)
    await db.commit()
    return {"flag_key": flag.flag_key, "flag_value": flag.flag_value}


# ------------------------------------------------------------------ #
# Maintenance mode
# ------------------------------------------------------------------ #

@router.get("/maintenance")
async def maintenance_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    in_maintenance = await svc.is_in_maintenance()
    return {"maintenance_mode": in_maintenance}


@router.post("/maintenance/enable")
async def enable_maintenance(
    body: MaintenanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.enable_maintenance(current_user.id, reason=body.reason)


@router.post("/maintenance/disable")
async def disable_maintenance(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.disable_maintenance(current_user.id)


# ------------------------------------------------------------------ #
# Maintenance windows
# ------------------------------------------------------------------ #

@router.get("/maintenance/windows")
async def list_windows(
    upcoming_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.list_windows(upcoming_only=upcoming_only)


@router.post("/maintenance/windows", status_code=201)
async def schedule_window(
    body: ScheduleWindowRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.schedule_window(current_user.id, body.model_dump())


@router.post("/maintenance/windows/{window_id}/activate")
async def activate_window(
    window_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.activate_window(window_id, current_user.id)


@router.post("/maintenance/windows/{window_id}/close")
async def close_window(
    window_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = MaintenanceService(db)
    return await svc.close_window(window_id, current_user.id)


# ------------------------------------------------------------------ #
# Restore validation
# ------------------------------------------------------------------ #

@router.get("/restore/validate")
async def validate_restore(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run post-restore integrity checks.
    Call this after every backup restore.
    """
    validator = RestoreValidator(db)
    return await validator.run_all_checks(tenant_id=current_user.tenant_id)


@router.get("/restore/validate/global")
async def validate_restore_global(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Run global checks (ledger balance across all tenants)."""
    validator = RestoreValidator(db)
    return await validator.run_all_checks(tenant_id=None)


# ------------------------------------------------------------------ #
# Factory Reset
# ------------------------------------------------------------------ #

@router.post("/factory-reset")
async def factory_reset(
    confirm: bool = Body(..., embed=True),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    DANGEROUS: Wipes the entire database and restarts from scratch.
    Only available to superusers.
    """
    if not current_user.is_superuser:
        raise ForbiddenError("Only superusers can perform factory reset.")

    if not confirm:
        return {"message": "Reset cancelled. Confirmation required."}

    # Ensure all models are loaded for metadata
    import app.models
    from sqlalchemy import text, MetaData
    import logging
    logger = logging.getLogger(__name__)

    import asyncio, os
    from fastapi import HTTPException

    # Build sync DSN — replace asyncpg driver
    raw_dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    # Determine environment and build correct DSN
    if "@db:" in raw_dsn:
        # Docker environment - keep "db" hostname as is
        sync_dsn = raw_dsn
    else:
        # Local environment - replace with localhost if needed
        sync_dsn = raw_dsn.replace("@db:", "@localhost:").replace("@db/", "@localhost/")

    def _do_reset_sync():
        import psycopg2
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command

        print(f"Starting factory reset nuclear sequence... DSN host: {sync_dsn.split('@')[-1]}")

        conn = psycopg2.connect(sync_dsn)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = current_database() AND pid <> pg_backend_pid();
        """)
        print("Terminated other connections.")

        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute("GRANT ALL ON SCHEMA public TO PUBLIC;")
        cur.close()
        conn.close()
        print("Schema dropped and recreated.")

        alembic_ini = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'alembic.ini')
        )
        print(f"Running Alembic from: {alembic_ini}")
        alembic_cfg = AlembicConfig(alembic_ini)
        alembic_command.upgrade(alembic_cfg, "head")
        print("Factory reset complete — all migrations applied.")

    try:
        # Close session first to avoid cleanup errors after schema drop
        await db.close()
        await engine.dispose()
        await asyncio.to_thread(_do_reset_sync)
    except Exception as e:
        print(f"CRITICAL: Factory reset failed: {str(e)}")
        logger.exception("Factory reset failed")
        raise HTTPException(status_code=500, detail=f"Factory reset failed: {str(e)}")

    return {
        "message": "System has been reset to factory settings. All data wiped.",
        "redirect": "/setup"
    }
