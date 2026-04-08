"""Backup management endpoints (superadmin only)."""
import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Body, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.backup_service import BackupService, _backup_dir

router = APIRouter(prefix="/backup", tags=["backup"])


@router.get("")
async def list_backups(current_user=Depends(get_current_user)):
    svc = BackupService()
    return svc.list_backups()


@router.post("", status_code=201)
async def create_backup(current_user=Depends(get_current_user)):
    svc = BackupService()
    return await svc.create_backup(actor_id=current_user.id)


@router.get("/{filename:path}/download")
async def download_backup(
    filename: str,
    current_user=Depends(get_current_user),
):
    """Download a backup file to client."""
    path = _backup_dir() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found.")
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=filename,
    )


@router.get("/{filename:path}/verify")
async def verify_backup(filename: str, current_user=Depends(get_current_user)):
    svc = BackupService()
    return svc.verify_backup(filename)


@router.post("/{filename:path}/restore")
async def restore_backup(
    filename: str,
    confirm: bool = Body(..., embed=True),
    current_user=Depends(get_current_user),
):
    if not confirm:
        return {"detail": "Restore cancelled. Set confirm=true to proceed."}
    svc = BackupService()
    return await svc.restore_backup(filename, actor_id=current_user.id)


@router.post("/upload-restore", status_code=200)
async def upload_and_restore(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a backup file and restore it immediately."""
    filename = file.filename or "uploaded_backup.sql.enc"
    if not (filename.endswith(".sql") or filename.endswith(".sql.enc")):
        raise HTTPException(status_code=400, detail="Geçersiz dosya türü. Sadece .sql veya .sql.enc dosyaları kabul edilir.")

    backup_path = _backup_dir() / filename
    content = await file.read()
    backup_path.write_bytes(content)

    svc = BackupService()
    return await svc.restore_backup(filename, actor_id=current_user.id)


@router.delete("/{filename:path}")
async def delete_backup(
    filename: str,
    current_user=Depends(get_current_user),
):
    """Delete a backup file and its manifest."""
    backup_dir = _backup_dir()
    backup_path = backup_dir / filename
    manifest_path = backup_dir / f"{filename}.manifest.json"

    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found.")

    backup_path.unlink()
    if manifest_path.exists():
        manifest_path.unlink()

    return {"deleted": filename}


@router.post("/purge/transactions")
async def purge_transactions_by_date(
    date_from: date,
    date_to: date,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Soft-delete all transactions (and their ledger entries) within a date range.
    Requires confirm=true. Reverses account balances accordingly.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="confirm=true gerekli.")
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Başlangıç tarihi bitiş tarihinden büyük olamaz.")

    svc = BackupService()
    return await svc.purge_transactions(db, current_user.tenant_id, date_from, date_to, current_user.id)
