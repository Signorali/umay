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

# ── Constants ─────────────────────────────────────────────────────────────────

_HUB_IMAGE_BACKEND  = "signorali/umay-backend"
_HUB_IMAGE_FRONTEND = "signorali/umay-frontend"
_CONTAINER_BACKEND  = "umay_backend"
_CONTAINER_FRONTEND = "umay_frontend"


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
    """Parse 'X.Y.Z' → (X, Y, Z) tuple for comparison."""
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


async def _get_latest_hub_version(image: str) -> Optional[str]:
    """Fetch the highest semver tag from Docker Hub for the given image."""
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
            t["name"]
            for t in results
            if re.match(r"^\d+\.\d+\.\d+$", t.get("name", ""))
        ]
        if not versions:
            return None
        versions.sort(key=_parse_version, reverse=True)
        return versions[0]
    except Exception as exc:
        log.warning("Docker Hub version check failed: %s", exc)
        return None


def _recreate_container(client, container_name: str, new_image: str) -> None:
    """
    Stop, remove, and recreate a container with a new image.
    Preserves port bindings, networks, volumes, environment variables,
    and restart policy from the original container.
    """
    old = client.containers.get(container_name)
    attrs = old.attrs
    cfg = attrs.get("Config", {})
    host_cfg = attrs.get("HostConfig", {})
    net_cfg = attrs.get("NetworkSettings", {}).get("Networks", {})

    # Preserve settings
    networks = list(net_cfg.keys())
    port_bindings = host_cfg.get("PortBindings") or {}
    binds = host_cfg.get("Binds") or []
    restart_policy = host_cfg.get("RestartPolicy", {"Name": "unless-stopped"})
    env = cfg.get("Env") or []

    # Stop and remove old container
    log.info("Stopping container %s …", container_name)
    old.stop(timeout=30)
    old.remove()
    log.info("Container %s removed.", container_name)

    # Build exposed_ports from port_bindings
    exposed_ports = {p: {} for p in port_bindings}

    # Create new container with updated image
    new_container = client.containers.create(
        f"{new_image}:latest",
        name=container_name,
        environment=env,
        ports=exposed_ports,
        volumes=binds,
        restart_policy=restart_policy,
        detach=True,
    )

    # Connect to all original networks
    primary_network = networks[0] if networks else "bridge"
    client.networks.get(primary_network).connect(new_container)
    new_container.start()
    log.info("Container %s recreated with image %s:latest.", container_name, new_image)


def _pull_and_restart_containers() -> tuple[bool, str]:
    """
    Synchronous worker (runs in thread-pool executor):
      1. Pull backend image
      2. Pull frontend image
      3. Recreate frontend container with new image (stop → remove → run)
    Returns (success, error_message).
    NOTE: docker restart alone does NOT use a new image; container must be recreated.
    """
    try:
        import docker as docker_sdk

        client = docker_sdk.from_env()

        log.info("Pulling %s:latest …", _HUB_IMAGE_BACKEND)
        client.images.pull(_HUB_IMAGE_BACKEND, tag="latest")

        log.info("Pulling %s:latest …", _HUB_IMAGE_FRONTEND)
        client.images.pull(_HUB_IMAGE_FRONTEND, tag="latest")

        # Recreate frontend with new image (safe — we're running in backend)
        _recreate_container(client, _CONTAINER_FRONTEND, _HUB_IMAGE_FRONTEND)

        return True, ""
    except Exception as exc:
        log.error("Pull/restart error: %s", exc)
        return False, str(exc)


async def _run_docker_update(log_id: str, _tenant_id: str) -> None:
    """
    Background task:
      - Pulls images & restarts frontend (via thread executor)
      - Saves result to UpdateLog
      - Schedules backend restart via a detached subprocess (so response survives)
    """
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
            success, error_msg = await loop.run_in_executor(
                None, _pull_and_restart_containers
            )

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
            log.error("Update task unhandled error: %s", exc)
            return

        if success:
            # Write a recreate script to /tmp, run it detached after 5s.
            # We capture backend container config NOW (while it's alive), write to
            # a JSON file, then the script reads that file and recreates the container.
            import docker as docker_sdk
            import json as _json
            import tempfile as _tmp
            import os as _os

            _script_path = "/tmp/umay_backend_recreate.py"
            _config_path = "/tmp/umay_backend_config.json"

            try:
                _client = docker_sdk.from_env()
                _old = _client.containers.get(_CONTAINER_BACKEND)
                _attrs = _old.attrs
                _config_data = {
                    "image": f"{_HUB_IMAGE_BACKEND}:latest",
                    "env": _attrs["Config"].get("Env") or [],
                    "binds": _attrs["HostConfig"].get("Binds") or [],
                    "restart_policy": _attrs["HostConfig"].get("RestartPolicy", {"Name": "unless-stopped"}),
                    "networks": list(_attrs["NetworkSettings"]["Networks"].keys()),
                    "container_name": _CONTAINER_BACKEND,
                }
                with open(_config_path, "w") as _f:
                    _json.dump(_config_data, _f)

                _script = """import docker, json, time
time.sleep(5)
with open('/tmp/umay_backend_config.json') as f:
    cfg = json.load(f)
c = docker.from_env()
try:
    old = c.containers.get(cfg['container_name'])
    old.stop(timeout=30)
    old.remove()
except Exception:
    pass
nc = c.containers.create(
    cfg['image'], name=cfg['container_name'],
    environment=cfg['env'], volumes=cfg['binds'],
    restart_policy=cfg['restart_policy'], detach=True,
)
networks = cfg.get('networks', [])
if networks:
    c.networks.get(networks[0]).connect(nc)
nc.start()
"""
                with open(_script_path, "w") as _f:
                    _f.write(_script)

                log.info("Scheduling backend recreation via script in 5 s …")
                subprocess.Popen(
                    ["python3", _script_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as _e:
                log.warning("Could not write recreate script (%s), falling back to docker restart", _e)
                subprocess.Popen(
                    f"sleep 5 && docker restart {_CONTAINER_BACKEND}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=UpdateStatusResponse)
async def get_update_status(
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_db),
):
    """
    Returns current version and latest available version from Docker Hub.
    Requires an active license (or active trial).
    """
    from app.core.config import settings

    redis = await get_redis()
    svc = LicenseService(session, redis)
    status = await svc.get_status_dict(current_user.tenant_id)

    current_version: str = settings.APP_VERSION or "1.0.0"

    is_active = status.get("is_licensed") or not status.get("is_expired")
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
    """
    Trigger a live update via Docker socket.
    Pulls signorali/umay-backend:latest and signorali/umay-frontend:latest,
    restarts both containers.  Backend container restarts last (detached).
    Requires superuser.
    """
    from app.core.config import settings

    current_version: str = settings.APP_VERSION or "1.0.0"

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
    """Get update history for the tenant (superuser only)."""
    result = await session.execute(
        select(UpdateLog)
        .where(UpdateLog.tenant_id == str(current_user.tenant_id))
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
