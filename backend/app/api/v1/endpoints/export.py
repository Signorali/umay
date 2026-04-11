"""Export endpoints — CSV, JSON, and diagnostics package."""
import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import io

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/transactions.csv")
async def export_transactions_csv(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    group_id: Optional[uuid.UUID] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Download all transactions as CSV (UTF-8 BOM for Excel compatibility)."""
    svc = ExportService(db)
    data = await svc.export_transactions_csv(
        current_user.tenant_id,
        date_from=date_from, date_to=date_to, group_id=group_id,
    )
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.get("/accounts.csv")
async def export_accounts_csv(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc = ExportService(db)
    data = await svc.export_accounts_csv(current_user.tenant_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=accounts.csv"},
    )


@router.get("/data.json")
async def export_full_json(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Full portable JSON export of all tenant data."""
    svc = ExportService(db)
    data = await svc.export_tenant_data_json(current_user.tenant_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=umay_export.json"},
    )


@router.get("/diagnostics.zip")
async def export_diagnostics(
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Download a diagnostics package (ZIP) with DB stats, manifest, and account CSV.
    Useful for support requests and system audits.
    """
    svc = ExportService(db)
    data = await svc.build_diagnostics_package(current_user.tenant_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=umay_diagnostics.zip"},
    )
