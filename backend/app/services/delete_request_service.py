"""Delete-request workflow service.

Non-admin users raise a DeleteRequest for records they cannot delete directly.
Tenant admins can approve (which executes the actual deletion) or reject.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delete_request import DeleteRequest, ALLOWED_TARGET_TABLES
from app.repositories.delete_request import DeleteRequestRepository
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleError, ForbiddenError


class DeleteRequestService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DeleteRequestRepository(session)
        self.audit = AuditService(session)

    async def create_request(
        self,
        tenant_id: uuid.UUID,
        requested_by_user_id: uuid.UUID,
        target_table: str,
        target_id: uuid.UUID,
        target_label: Optional[str],
        reason: Optional[str],
        actor_email: Optional[str] = None,
    ) -> DeleteRequest:
        if target_table not in ALLOWED_TARGET_TABLES:
            raise BusinessRuleError(f"Delete requests are not supported for table '{target_table}'")

        existing = await self.repo.get_pending_for_target(target_table, target_id, tenant_id)
        if existing:
            raise ConflictError("A pending delete request already exists for this record")

        req = DeleteRequest(
            tenant_id=tenant_id,
            requested_by_user_id=requested_by_user_id,
            target_table=target_table,
            target_id=target_id,
            target_label=target_label,
            reason=reason,
            status="pending",
        )
        req = await self.repo.create(req)

        await self.audit.log(
            action="DELETE_REQUEST_CREATED",
            module="delete_requests",
            tenant_id=tenant_id,
            actor_id=requested_by_user_id,
            actor_email=actor_email,
            record_id=str(req.id),
            after={
                "target_table": target_table,
                "target_id": str(target_id),
                "target_label": target_label,
            },
        )
        return req

    async def list_pending(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeleteRequest], int]:
        return await self.repo.list_by_tenant(tenant_id, status=status, offset=offset, limit=limit)

    async def list_my_requests(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[DeleteRequest], int]:
        return await self.repo.list_by_user(user_id, tenant_id, offset=offset, limit=limit)

    async def approve(
        self,
        request_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        reviewer_email: Optional[str] = None,
    ) -> DeleteRequest:
        req = await self.repo.get_by_id(request_id)
        if not req or req.tenant_id != tenant_id:
            raise NotFoundError("DeleteRequest")
        if req.status != "pending":
            raise ConflictError(f"Request is already '{req.status}'")

        # Execute the actual deletion (soft-delete via is_deleted flag)
        await self._soft_delete_record(req.target_table, req.target_id, tenant_id)

        req = await self.repo.update(
            req,
            status="approved",
            reviewed_by_user_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
        )

        await self.audit.log(
            action="DELETE_REQUEST_APPROVED",
            module="delete_requests",
            tenant_id=tenant_id,
            actor_id=reviewer_id,
            actor_email=reviewer_email,
            record_id=str(req.id),
            after={
                "target_table": req.target_table,
                "target_id": str(req.target_id),
            },
        )
        return req

    async def reject(
        self,
        request_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        reject_reason: Optional[str] = None,
        reviewer_email: Optional[str] = None,
    ) -> DeleteRequest:
        req = await self.repo.get_by_id(request_id)
        if not req or req.tenant_id != tenant_id:
            raise NotFoundError("DeleteRequest")
        if req.status != "pending":
            raise ConflictError(f"Request is already '{req.status}'")

        req = await self.repo.update(
            req,
            status="rejected",
            reviewed_by_user_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
            reject_reason=reject_reason,
        )

        await self.audit.log(
            action="DELETE_REQUEST_REJECTED",
            module="delete_requests",
            tenant_id=tenant_id,
            actor_id=reviewer_id,
            actor_email=reviewer_email,
            record_id=str(req.id),
            before={"reason": reject_reason},
        )
        return req

    async def _soft_delete_record(
        self, table: str, record_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> None:
        """Soft-delete the target record by setting is_deleted = true."""
        # Table name is validated against ALLOWED_TARGET_TABLES before reaching here
        stmt = text(
            f"UPDATE {table} SET is_deleted = true "
            "WHERE id = :record_id AND tenant_id = :tenant_id AND is_deleted = false"
        )
        result = await self.session.execute(
            stmt, {"record_id": record_id, "tenant_id": tenant_id}
        )
        if result.rowcount == 0:
            raise NotFoundError(f"Record in '{table}'")
