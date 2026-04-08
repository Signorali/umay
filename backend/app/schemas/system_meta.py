"""System meta schemas — SystemFlag and MaintenanceWindow API contracts."""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── SystemFlag ────────────────────────────────────────────────────────────────

class SystemFlagOut(BaseModel):
    id: uuid.UUID
    flag_key: str
    flag_value: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[uuid.UUID] = None
    updated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemFlagUpsertIn(BaseModel):
    flag_key: str = Field(..., min_length=1, max_length=100)
    flag_value: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)


class SystemFlagListOut(BaseModel):
    items: List[SystemFlagOut]
    total: int


# ── MaintenanceWindow ─────────────────────────────────────────────────────────

class MaintenanceWindowOut(BaseModel):
    id: uuid.UUID
    label: str
    reason: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceWindowCreateIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=200)
    reason: Optional[str] = Field(None, max_length=1000)
    scheduled_start: datetime
    scheduled_end: datetime


class MaintenanceWindowListOut(BaseModel):
    items: List[MaintenanceWindowOut]
    is_currently_active: bool
