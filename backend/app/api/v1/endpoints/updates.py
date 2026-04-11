"""
updates.py — Update management endpoints (Docker Socket implementation)

GET  /updates/status   — Check Docker Hub for latest version
POST /updates/trigger  — Pull latest images & restart containers (admin only)
GET  /updates/logs     — Update history (admin only)
"""

import asyncio
import logging
import re
import subprocess
import uuid as _uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_superuser, get_current_user
from app.core.database import get_db, AsyncSessionLocal
from app.core.exceptions import BadRequestError
from app.models.user import User
from app.models.update import UpdateLog
from app.services.license_service import LicenseService
from app.core.redis_client import get_redis

log = logging.getLogger(__name__)

router = APIRouter(prefix="/updates", tags=["updates"])

def _current_version() -> str:
    """Read version from baked-in file first (immune to .env overrides), fallback to ENV."""
    try:
        v = open("/app/VERSION").read().strip()
        if v:
            return v
    except Exception:
        pass
    from app.core.config import settings as _settings
    return os.environ.get("APP_VERSION", _settings.APP_VERSION)


# ── Constants ─────────────────────────────────────────────────────────────────

_HUB_IMAGE_BACKEND  = os.environ.get("DOCKER_IMAGE_BACKEND", "signorali/umay-backend")
_HUB_IMAGE_FRONTEND = os.environ.get("DOCKER_IMAGE_FRONTEND", "signorali/umay-frontend")

# Docker Compose service names (label-based lookup — works regardless of container name)
_SERVICE_BACKEND  = "backend"
_SERVICE_FRONTEND = "frontend"


# ── Schemas ───────────────────────────────────────────────────────────────────

class UpdateStatusResponse(BaseModel):
    version: str
    latest_version: Optional[str] = None
    has_update: bool = False


class UpdateTriggerResponse(BaseModel):
    message: str
    update_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


async def _get_latest_hub_version(image: str) -> Optional[str]:
    """Fetch the highest semver tag from Docker Hub."""
    url = (
        f"https://hub.docker.com/v2/repositories/{image}/tags/"
        f"?page_size=50&ordering=last_updated"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            results = r.json().get("results", [])
        versions = [
            t["name"] for t in results
            if re.match(r"^\d+\.\d+\.\d+$", t.get("name", ""))
        ]
        if not versions:
            return None
        versions.sort(key=_parse_version, reverse=True)
        return versions[0]
    except Exception as exc:
        log.warning("Docker Hub version check failed: %s", exc)
        return None


def _find_container(client, service_name: str):
    """
    Find a container by Docker Compose service label.
    Works regardless of container naming convention (umay_backend vs umay-backend-1).
    """
    containers = client.containers.list(
        filters={"label": f"com.docker.compose.service={service_name}"}
    )
    if not containers:
        raise RuntimeError(
            f"No container found with label com.docker.compose.service={service_name}"
        )
    return containers[0]


def _pull_and_restart_sync() -> tuple[bool, str]:
    """
    Pull latest images and recreate the frontend container.
    Backend recreation is handled separately via a detached subprocess.
    """
    try:
        import docker as docker_sdk

        client = docker_sdk.from_env()

        log.info("Pulling %s:latest …", _HUB_IMAGE_BACKEND)
        client.images.pull(_HUB_IMAGE_BACKEND, tag="latest")

        log.info("Pulling %s:latest …", _HUB_IMAGE_FRONTEND)
        client.images.pull(_HUB_IMAGE_FRONTEND, tag="latest")

        # Recreate frontend (safe since we run in backend)
        frontend = _find_container(client, _SERVICE_FRONTEND)
        frontend_name = frontend.name
        attrs      = frontend.attrs
        cfg        = attrs["Config"]
        host_cfg   = attrs["HostConfig"]
        networks   = list(attrs["NetworkSettings"]["Networks"].keys())

        # Build ports dict for docker-py
        ports_dict: dict = {}
        for cport, bindings in (host_cfg.get("PortBindings") or {}).items():
            if bindings:
                hp_str = bindings[0].get("HostPort", "")
                h_ip   = bindings[0].get("HostIp", "")
                if hp_str:
                    hp = int(hp_str)
                    ports_dict[cport] = (h_ip, hp) if h_ip else hp

        primary_net = next(
            (n for n in networks if n not in ("bridge", "host", "none")),
            networks[0] if networks else "bridge",
        )

        log.info("Recreating frontend container %s …", frontend_name)
        frontend.stop(timeout=30)
        frontend.remove()

        new_fe = client.containers.create(
            f"{_HUB_IMAGE_FRONTEND}:latest",
            name=frontend_name,
            environment=cfg.get("Env") or [],
            ports=ports_dict,
            volumes=host_cfg.get("Binds") or [],
            restart_policy=host_cfg.get("RestartPolicy", {"Name": "unless-stopped"}),
            network=primary_net,
            detach=True,
        )
        new_fe.start()
        log.info("Frontend recreated successfully.")

        return True, ""
    except Exception as exc:
        log.error("Pull/restart error: %s", exc)
        return False, str(exc)


def _schedule_backend_recreate() -> None:
    """
    Write a standalone Python script to /tmp and run it detached.
    The script waits 5s, then recreates the backend container with the new image.
    It uses Docker Compose service labels so it works on any naming convention.
    """
    script = f"""
import docker, time, sys
time.sleep(5)
try:
    client = docker.from_env()
    containers = client.containers.list(
        filters={{"label": "com.docker.compose.service={_SERVICE_BACKEND}"}}
    )
    if not containers:
        print("Backend container not found via label, aborting.", file=sys.stderr)
        sys.exit(1)

    old = containers[0]
    name = old.name
    attrs = old.attrs
    cfg = attrs["Config"]
    hcfg = attrs["HostConfig"]
    networks = list(attrs["NetworkSettings"]["Networks"].keys())

    ports_dict = {{}}
    for cport, bindings in (hcfg.get("PortBindings") or {{}}).items():
        if bindings:
            hp_str = bindings[0].get("HostPort", "")
            h_ip = bindings[0].get("HostIp", "")
            if hp_str:
                hp = int(hp_str)
                ports_dict[cport] = (h_ip, hp) if h_ip else hp

    primary_net = next(
        (n for n in networks if n not in ("bridge", "host", "none")),
        networks[0] if networks else "bridge",
    )

    old.stop(timeout=30)
    old.remove()

    nc = client.containers.create(
        "{_HUB_IMAGE_BACKEND}:latest",
        name=name,
        environment=cfg.get("Env") or [],
        ports=ports_dict,
        volumes=hcfg.get("Binds") or [],
        restart_policy=hcfg.get("RestartPolicy", {{"Name": "unless-stopped"}}),
        network=primary_net,
        detach=True,
    )
    nc.start()
    print(f"Backend recreated as {{name}}.")
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
"""
    script_path = "/tmp/umay_backend_recreate.py"
    with open(script_path, "w") as f:
        f.write(script)

    subprocess.Popen(
        ["python3", script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    log.info("Backend recreation script scheduled (5 s delay).")


async def _run_docker_update(log_id: str, _tenant_id: str) -> None:
    """Background task: pull images, recreate containers, update log."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UpdateLog).where(UpdateLog.id == _uuid.UUID(log_id))
        )
        update_log = result.scalar_one_or_none()
        if not update_log:
            log.error("UpdateLog %s not found", log_id)
            return

        update_log.started_at = datetime.now(timezone.utc)
        update_log.status = "running"
        await session.commit()

        try:
            loop = asyncio.get_event_loop()
            success, error_msg = await loop.run_in_executor(None, _pull_and_restart_sync)

            if success:
                update_log.status = "success"
                update_log.output = (
                    "İmajlar çekildi, frontend yeniden başlatıldı. "
                    "Backend birkaç saniye içinde yeniden başlayacak."
                )
            else:
                update_log.status = "failed"
                update_log.error = error_msg

            update_log.completed_at = datetime.now(timezone.utc)
            await session.commit()

        except Exception as exc:
            update_log.status = "failed"
            update_log.error = str(exc)
            update_log.completed_at = datetime.now(timezone.utc)
            await session.commit()
            log.error("Update task error: %s", exc)
            return

        if success:
            try:
                _schedule_backend_recreate()
            except Exception as exc:
                log.warning("Could not schedule backend recreate: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=UpdateStatusResponse)
async def get_update_status(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    svc = LicenseService(session, redis)
    status_dict = await svc.get_status_dict(current_user.tenant_id)

    current_version: str = _current_version()

    is_active = status_dict.get("is_licensed") or not status_dict.get("is_expired")
    if not is_active:
        raise BadRequestError(
            "Sistem lisanssız ve deneme süresi bitmiş. Güncelleme yapılamaz."
        )

    latest_version = await _get_latest_hub_version(_HUB_IMAGE_BACKEND)
    has_update = (
        _parse_version(latest_version) > _parse_version(current_version)
        if latest_version
        else False
    )

    return UpdateStatusResponse(
        version=current_version,
        latest_version=latest_version,
        has_update=has_update,
    )


@router.post("/trigger", response_model=UpdateTriggerResponse)
async def trigger_update(
    current_user: Annotated[User, Depends(get_current_superuser)],
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    current_version: str = _current_version()

    update_log = UpdateLog(
        tenant_id=current_user.tenant_id,
        version=current_version,
        status="pending",
    )
    session.add(update_log)
    await session.commit()
    await session.refresh(update_log)

    background_tasks.add_task(
        _run_docker_update,
        str(update_log.id),
        str(current_user.tenant_id),
    )

    return UpdateTriggerResponse(
        message=(
            "Güncelleme başlatıldı. İmajlar çekiliyor, kapsayıcılar "
            "yeniden başlatılacak. Birkaç dakika sonra sayfayı yenileyin."
        ),
        update_id=str(update_log.id),
    )


@router.get("/logs")
async def get_update_logs(
    current_user: Annotated[User, Depends(get_current_superuser)],
    session: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    result = await session.execute(
        select(UpdateLog)
        .where(UpdateLog.tenant_id == current_user.tenant_id)
        .order_by(UpdateLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(entry.id),
                "version": entry.version,
                "status": entry.status,
                "started_at": entry.started_at,
                "completed_at": entry.completed_at,
                "error": entry.error,
                "output": entry.output,
                "duration_seconds": (
                    (entry.completed_at - entry.started_at).total_seconds()
                    if entry.completed_at and entry.started_at
                    else None
                ),
            }
            for entry in logs
        ]
    }
