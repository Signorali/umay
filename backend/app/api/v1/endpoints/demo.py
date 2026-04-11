"""Demo mode endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.services.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/status")
async def demo_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Returns whether demo mode is active for this tenant."""
    svc = DemoService(db)
    return await svc.get_status(current_user.tenant_id)


@router.post("/activate", status_code=201)
async def activate_demo(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Seed demo data (~5 records per module).
    Demo records are isolated and fully removable.
    """
    svc = DemoService(db)
    return await svc.activate_demo(current_user.tenant_id, current_user.id)


@router.delete("/deactivate")
async def deactivate_demo(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Remove all demo data safely without touching real business records."""
    svc = DemoService(db)
    return await svc.deactivate_demo(current_user.tenant_id, current_user.id)
