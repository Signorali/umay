"""AuditLog schemas — response contracts for audit trail queries."""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    tenant_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: str
    module: str
    record_id: Optional[str] = None
    before_data: Optional[str] = None
    after_data: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditLogListOut(BaseModel):
    items: List[AuditLogOut]
    total: int


class AuditLogFilterIn(BaseModel):
    """Query parameters for filtering audit logs."""
    module: Optional[str] = None
    action: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    record_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)
