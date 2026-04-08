"""Backup schemas — request/response contracts for backup and restore operations."""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BackupStatusOut(BaseModel):
    """Backup system health/status summary."""
    last_backup_at: Optional[datetime] = None
    last_backup_size_bytes: Optional[int] = None
    last_backup_status: Optional[str] = None  # "ok" | "failed" | "running"
    backup_path: Optional[str] = None
    auto_backup_enabled: bool = False


class BackupCreateIn(BaseModel):
    """Trigger a manual backup."""
    label: Optional[str] = Field(None, max_length=200)
    include_attachments: bool = True


class BackupJobOut(BaseModel):
    """Response when a backup job is enqueued."""
    job_id: str
    status: str = "enqueued"
    message: str


class RestoreVerifyIn(BaseModel):
    """Trigger a restore verification against a backup file."""
    backup_path: str = Field(..., min_length=1)
    dry_run: bool = True


class RestoreVerifyOut(BaseModel):
    """Result of a restore verification run."""
    is_valid: bool
    backup_path: str
    checksum_ok: bool
    schema_version: Optional[str] = None
    record_counts: Optional[Dict[str, int]] = None
    errors: List[str] = []
    warnings: List[str] = []
