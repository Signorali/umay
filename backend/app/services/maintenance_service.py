"""
MaintenanceService — maintenance mode control and update flow hooks.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_meta import SystemFlag, MaintenanceWindow
from app.services.audit_service import AuditService


class MaintenanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ #
    # System flags
    # ------------------------------------------------------------------ #

    async def get_flag(self, key: str) -> Optional[str]:
        q = select(SystemFlag).where(SystemFlag.flag_key == key)
        flag = (await self.db.execute(q)).scalar_one_or_none()
        return flag.flag_value if flag else None

    async def set_flag(self, key: str, value: str, actor_id: Optional[uuid.UUID] = None) -> SystemFlag:
        q = select(SystemFlag).where(SystemFlag.flag_key == key)
        flag = (await self.db.execute(q)).scalar_one_or_none()
        if flag:
            flag.flag_value = value
            if actor_id:
                flag.updated_by = actor_id
        else:
            flag = SystemFlag(flag_key=key, flag_value=value, updated_by=actor_id)
            self.db.add(flag)
        await self.db.flush()
        return flag

    async def get_all_flags(self) -> dict:
        q = select(SystemFlag)
        flags = list((await self.db.execute(q)).scalars().all())
        return {f.flag_key: f.flag_value for f in flags}

    # ------------------------------------------------------------------ #
    # Maintenance mode
    # ------------------------------------------------------------------ #

    async def is_in_maintenance(self) -> bool:
        val = await self.get_flag("maintenance_mode")
        return val == "true"

    async def enable_maintenance(
        self, actor_id: uuid.UUID, reason: Optional[str] = None
    ) -> dict:
        await self.set_flag("maintenance_mode", "true", actor_id)
        await self.audit.log(
            actor_id=actor_id, action="maintenance.enable",
            module="system", record_id=None,
            new_state={"reason": reason},
        )
        await self.db.commit()
        return {"maintenance_mode": True, "reason": reason}

    async def disable_maintenance(self, actor_id: uuid.UUID) -> dict:
        await self.set_flag("maintenance_mode", "false", actor_id)
        await self.audit.log(
            actor_id=actor_id, action="maintenance.disable",
            module="system", record_id=None,
        )
        await self.db.commit()
        return {"maintenance_mode": False}

    # ------------------------------------------------------------------ #
    # Maintenance windows
    # ------------------------------------------------------------------ #

    async def schedule_window(
        self, actor_id: uuid.UUID, data: dict
    ) -> MaintenanceWindow:
        window = MaintenanceWindow(created_by=actor_id, **data)
        self.db.add(window)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def list_windows(self, upcoming_only: bool = True) -> list:
        q = select(MaintenanceWindow).where(MaintenanceWindow.is_deleted == False)
        if upcoming_only:
            q = q.where(MaintenanceWindow.scheduled_end >= datetime.now(timezone.utc))
        q = q.order_by(MaintenanceWindow.scheduled_start)
        return list((await self.db.execute(q)).scalars().all())

    async def activate_window(self, window_id: uuid.UUID, actor_id: uuid.UUID) -> MaintenanceWindow:
        q = select(MaintenanceWindow).where(
            MaintenanceWindow.id == window_id,
            MaintenanceWindow.is_deleted == False,
        )
        window = (await self.db.execute(q)).scalar_one_or_none()
        if not window:
            raise HTTPException(status_code=404, detail="Maintenance window not found.")
        window.is_active = True
        window.actual_start = datetime.now(timezone.utc)
        await self.enable_maintenance(actor_id, reason=window.reason)
        await self.db.commit()
        await self.db.refresh(window)
        return window

    async def close_window(self, window_id: uuid.UUID, actor_id: uuid.UUID) -> MaintenanceWindow:
        q = select(MaintenanceWindow).where(
            MaintenanceWindow.id == window_id,
            MaintenanceWindow.is_deleted == False,
        )
        window = (await self.db.execute(q)).scalar_one_or_none()
        if not window:
            raise HTTPException(status_code=404, detail="Maintenance window not found.")
        window.is_active = False
        window.actual_end = datetime.now(timezone.utc)
        await self.disable_maintenance(actor_id)
        await self.db.commit()
        await self.db.refresh(window)
        return window
