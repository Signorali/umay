"""
Period Locking Service — prevent modifications to closed accounting periods.

Design rules (cloud.md §16):
  - A period is YEAR-MONTH (e.g., 2025-01)
  - Once locked, NO transaction (create/update/delete) targeting that period is allowed
  - Exceptions: superuser override with explicit `force=True`
  - Lock state is stored in system_flags as JSON: {"locked": ["2025-01", "2025-02"]}
  - Unlocking requires tenant_admin; locking is irreversible without explicit unlock
  - Reversal transactions that reference a locked source are allowed (create in current period)
"""
import json
import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.system_meta import SystemFlag
from app.services.audit_service import AuditService
from app.core.exceptions import BusinessRuleError

PERIOD_LOCK_FLAG_KEY = "locked_periods"


class PeriodLockService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit = AuditService(session)

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_locked_periods(self) -> List[str]:
        """Return list of locked periods as 'YYYY-MM' strings."""
        flag = await self._get_flag()
        if not flag:
            return []
        try:
            data = json.loads(flag.flag_value or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    async def lock_period(
        self,
        year: int,
        month: int,
        actor_id: uuid.UUID,
        actor_email: str,
        tenant_id: uuid.UUID,
    ) -> List[str]:
        """
        Lock a period. Returns updated locked periods list.
        Idempotent: locking an already-locked period is a no-op.
        """
        period = f"{year:04d}-{month:02d}"
        locked = await self.get_locked_periods()
        if period in locked:
            return locked  # already locked

        locked.append(period)
        locked.sort()
        await self._upsert_flag(locked)

        await self.audit.log(
            action="PERIOD_LOCK",
            module="period_lock",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            after={"period": period, "all_locked": locked},
        )
        return locked

    async def unlock_period(
        self,
        year: int,
        month: int,
        actor_id: uuid.UUID,
        actor_email: str,
        tenant_id: uuid.UUID,
    ) -> List[str]:
        """
        Unlock a previously locked period (admin action, audit logged).
        Returns updated locked periods list.
        """
        period = f"{year:04d}-{month:02d}"
        locked = await self.get_locked_periods()
        if period not in locked:
            return locked  # nothing to unlock

        locked = [p for p in locked if p != period]
        await self._upsert_flag(locked)

        await self.audit.log(
            action="PERIOD_UNLOCK",
            module="period_lock",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            after={"period": period, "all_locked": locked},
        )
        return locked

    async def assert_period_open(
        self,
        transaction_date: date,
        force: bool = False,
    ) -> None:
        """
        Raise BusinessRuleError if the date falls in a locked period.
        Call this before creating/updating/deleting any transaction.
        force=True is reserved for superuser override.
        """
        if force:
            return  # superuser bypass

        period = f"{transaction_date.year:04d}-{transaction_date.month:02d}"
        locked = await self.get_locked_periods()
        if period in locked:
            raise BusinessRuleError(
                f"Dönem kapalıdır ve değişiklik yapılamaz: {period}. "
                "Bu dönemi açmak için yönetici ile iletişime geçin."
            )

    async def is_period_locked(self, year: int, month: int) -> bool:
        """Quick check — returns True if the given period is locked."""
        period = f"{year:04d}-{month:02d}"
        locked = await self.get_locked_periods()
        return period in locked

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_flag(self) -> Optional[SystemFlag]:
        result = await self.session.execute(
            select(SystemFlag).where(SystemFlag.flag_key == PERIOD_LOCK_FLAG_KEY)
        )
        return result.scalar_one_or_none()

    async def _upsert_flag(self, locked: List[str]) -> None:
        flag = await self._get_flag()
        new_value = json.dumps(locked)
        if flag:
            flag.flag_value = new_value
        else:
            flag = SystemFlag(
                flag_key=PERIOD_LOCK_FLAG_KEY,
                flag_value=new_value,
                description="Kapalı muhasebe dönemleri (YYYY-MM formatı)",
            )
            self.session.add(flag)
        await self.session.flush()
