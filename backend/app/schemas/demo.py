"""Demo mode schemas — request/response contracts for demo data management."""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class DemoSessionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    started_by: Optional[uuid.UUID] = None
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime] = None
    seeded_modules: Optional[str] = None
    seed_record_ids: Optional[Dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DemoSeedResultOut(BaseModel):
    """Result returned after seeding demo data."""
    session_id: uuid.UUID
    seeded_modules: List[str]
    record_counts: Dict[str, int]
    message: str


class DemoCleanupResultOut(BaseModel):
    """Result returned after removing demo data."""
    removed_modules: List[str]
    removed_counts: Dict[str, int]
    message: str


class DemoStatusOut(BaseModel):
    """Indicates whether demo data is currently active for the tenant."""
    is_active: bool
    session: Optional[DemoSessionOut] = None
