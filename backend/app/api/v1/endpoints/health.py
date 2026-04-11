"""
Health check endpoints.

GET /health         — Full system health: db, redis, queue, backup, ledger
GET /health/ready   — Kubernetes readiness probe (fast, no auth)
GET /health/live    — Kubernetes liveness probe (fast, no auth)
GET /health/detail  — Detailed diagnostic (superuser only)
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.config import settings
from app.api.deps import get_current_user, get_current_superuser
from app.models.user import User

router = APIRouter()


async def _check_db(session: AsyncSession) -> dict:
    try:
        result = await session.execute(text("SELECT version()"))
        version = result.scalar_one()
        return {"status": "ok", "version": version[:40]}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:100]}


async def _check_redis() -> dict:
    try:
        redis = await get_redis()
        pong = await redis.ping()
        info = await redis.info("server")
        version = info.get("redis_version", "?")
        return {"status": "ok" if pong else "error", "version": version}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:100]}


async def _check_storage() -> dict:
    path = settings.STORAGE_PATH
    try:
        accessible = os.path.isdir(path) and os.access(path, os.W_OK)
        usage = {}
        if accessible:
            stat = os.statvfs(path) if hasattr(os, "statvfs") else None
            if stat:
                total_gb = round(stat.f_frsize * stat.f_blocks / 1e9, 2)
                free_gb = round(stat.f_frsize * stat.f_bfree / 1e9, 2)
                usage = {"total_gb": total_gb, "free_gb": free_gb}
        return {"status": "ok" if accessible else "error", "path": path, **usage}
    except Exception as exc:
        return {"status": "error", "path": path, "detail": str(exc)[:100]}


async def _check_backup() -> dict:
    path = settings.BACKUP_PATH
    try:
        exists = os.path.isdir(path)
        if not exists:
            return {"status": "warning", "path": path, "detail": "Backup path missing"}
        entries = sorted(
            [f for f in os.listdir(path) if f.endswith(".dump")],
            reverse=True,
        )
        last_backup = entries[0] if entries else None
        return {
            "status": "ok" if last_backup else "warning",
            "path": path,
            "last_backup": last_backup,
            "backup_count": len(entries),
        }
    except Exception as exc:
        return {"status": "error", "path": path, "detail": str(exc)[:100]}





async def _check_ledger(session: AsyncSession) -> dict:
    """Quick ledger integrity check: debit sum == credit sum."""
    try:
        from app.models.ledger import LedgerEntry
        result = await session.execute(
            select(
                LedgerEntry.entry_type,
                func.sum(LedgerEntry.amount).label("total"),
            )
            .where(LedgerEntry.is_deleted == False)
            .group_by(LedgerEntry.entry_type)
        )
        rows = {r.entry_type: float(r.total or 0) for r in result.all()}
        debit = rows.get("DEBIT", 0.0)
        credit = rows.get("CREDIT", 0.0)
        diff = abs(debit - credit)
        balanced = diff < 0.01  # allow tiny float rounding
        return {
            "status": "ok" if balanced else "error",
            "debit_total": debit,
            "credit_total": credit,
            "difference": diff,
            "balanced": balanced,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:100]}


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    """
    Public health summary — cloud.md §23.
    Returns aggregated status without sensitive details.
    """
    db = await _check_db(session)
    redis = await _check_redis()
    storage = await _check_storage()
    backup = await _check_backup()

    all_checks = [db["status"], redis["status"], storage["status"]]
    overall = "ok" if all(s == "ok" for s in all_checks) else (
        "degraded" if any(s == "error" for s in all_checks) else "warning"
    )

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db["status"],
            "redis": redis["status"],
            "storage": storage["status"],
            "backup": backup["status"],
        },
    }


@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe — fast, no DB."""
    return {"ready": True}


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe — fast, no DB."""
    return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/detail")
async def health_detail(
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
):
    """
    Detailed health diagnostics — superuser only.
    """
    db = await _check_db(session)
    redis = await _check_redis()
    storage = await _check_storage()
    backup = await _check_backup()
    ledger = await _check_ledger(session)

    # Queue depth (approximate via Redis list length)
    queue_status: dict = {}
    try:
        r = await get_redis()
        arq_key = "arq:queue"
        queue_len = await r.llen(arq_key)
        queue_status = {"status": "ok", "depth": queue_len}
    except Exception as exc:
        queue_status = {"status": "error", "detail": str(exc)[:80]}

    all_statuses = [
        db["status"], redis["status"], storage["status"],
        backup["status"], ledger["status"],
    ]
    overall = "ok" if all(s == "ok" for s in all_statuses) else (
        "degraded" if any(s == "error" for s in all_statuses) else "warning"
    )

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db,
            "redis": redis,
            "storage": storage,
            "backup": backup,
            "ledger_integrity": ledger,
            "queue": queue_status,
        },
    }
