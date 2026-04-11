"""
SystemMeta Repository — data access for SystemFlag and MaintenanceWindow.

Usage:
  - SystemFlag: key-value store for app-wide settings (maintenance mode, feature flags,
    locked periods, last backup timestamp, etc.)
  - MaintenanceWindow: scheduled or live maintenance windows
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_meta import SystemFlag, MaintenanceWindow


class SystemFlagRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, flag_key: str) -> Optional[SystemFlag]:
        result = await self.session.execute(
            select(SystemFlag).where(SystemFlag.flag_key == flag_key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, flag_key: str, default: Optional[str] = None) -> Optional[str]:
        flag = await self.get(flag_key)
        return flag.flag_value if flag else default

    async def list_all(self) -> List[SystemFlag]:
        result = await self.session.execute(
            select(SystemFlag).order_by(SystemFlag.flag_key)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        flag_key: str,
        flag_value: str,
        description: Optional[str] = None,
        updated_by: Optional[uuid.UUID] = None,
    ) -> SystemFlag:
        """Create or update a system flag."""
        existing = await self.get(flag_key)
        if existing:
            existing.flag_value = flag_value
            if description is not None:
                existing.description = description
            if updated_by is not None:
                existing.updated_by = updated_by
            await self.session.flush()
            return existing

        flag = SystemFlag(
            flag_key=flag_key,
            flag_value=flag_value,
            description=description,
            updated_by=updated_by,
        )
        self.session.add(flag)
        await self.session.flush()
        await self.session.refresh(flag)
        return flag

    async def delete(self, flag_key: str) -> bool:
        flag = await self.get(flag_key)
        if not flag:
            return False
        await self.session.delete(flag)
        await self.session.flush()
        return True


class MaintenanceWindowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, window_id: uuid.UUID) -> Optional[MaintenanceWindow]:
        return await self.session.get(MaintenanceWindow, window_id)

    async def list_active(self) -> List[MaintenanceWindow]:
        """Return currently active maintenance windows."""
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(MaintenanceWindow).where(
                MaintenanceWindow.is_active == True,
                MaintenanceWindow.scheduled_start <= now,
                MaintenanceWindow.scheduled_end >= now,
            )
        )
        return list(result.scalars().all())

    async def list_all(
        self, include_past: bool = False, limit: int = 20
    ) -> List[MaintenanceWindow]:
        q = select(MaintenanceWindow)
        if not include_past:
            q = q.where(MaintenanceWindow.scheduled_end >= datetime.now(timezone.utc))
        result = await self.session.execute(
            q.order_by(MaintenanceWindow.scheduled_start.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, window: MaintenanceWindow) -> MaintenanceWindow:
        self.session.add(window)
        await self.session.flush()
        await self.session.refresh(window)
        return window

    async def set_active(self, window_id: uuid.UUID, active: bool) -> Optional[MaintenanceWindow]:
        window = await self.get_by_id(window_id)
        if not window:
            return None
        window.is_active = active
        if active:
            window.actual_start = datetime.now(timezone.utc)
        else:
            window.actual_end = datetime.now(timezone.utc)
        await self.session.flush()
        return window
