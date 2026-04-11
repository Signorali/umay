import json
import uuid
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    """Writes immutable audit records. Must be called for every critical change."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        module: str,
        *,
        tenant_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
        record_id: Optional[str] = None,
        before: Optional[Any] = None,
        after: Optional[Any] = None,
        # Aliases for backward compatibility
        old_state: Optional[Any] = None,
        new_state: Optional[Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AuditLog:
        # Resolve aliases
        effective_before = before if before is not None else old_state
        effective_after = after if after is not None else new_state

        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            module=module,
            record_id=str(record_id) if record_id else None,
            before_data=json.dumps(effective_before, default=str) if effective_before is not None else None,
            after_data=json.dumps(effective_after, default=str) if effective_after is not None else None,
            ip_address=ip_address,
            user_agent=user_agent,
            notes=notes,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry
