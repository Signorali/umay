import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class DeleteRequestCreate(BaseModel):
    target_table: str
    target_id: uuid.UUID
    target_label: Optional[str] = None
    reason: Optional[str] = None


class DeleteRequestResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    target_table: str
    target_id: uuid.UUID
    target_label: Optional[str]
    reason: Optional[str]
    status: str
    reviewed_by_user_id: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    reject_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DeleteRequestReview(BaseModel):
    reject_reason: Optional[str] = None  # only for rejections
