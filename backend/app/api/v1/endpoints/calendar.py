"""Calendar endpoints — view upcoming obligations and trigger sync."""
import uuid
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.config import settings
from app.services.calendar_service import CalendarService
from app.services.external_calendar_service import ExternalCalendarService, get_oauth_config, _set_flag
from app.models.user import User
from pydantic import BaseModel

class OAuthCredentials(BaseModel):
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = ""
    microsoft_tenant_id: str = "common"

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("")
async def get_calendar_items(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    item_type: Optional[str] = Query(None),
    include_completed: bool = Query(False),
    include_dismissed: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    svc = CalendarService(db)
    return await svc.get_items(
        current_user.id, current_user.tenant_id,
        date_from=date_from, date_to=date_to,
        item_type=item_type,
        include_completed=include_completed,
        include_dismissed=include_dismissed,
        skip=skip, limit=limit,
    )


@router.post("/sync")
async def sync_calendar(
    months_ahead: int = Query(3, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "sync")),
):
    """
    Rebuild calendar items from current financial obligations.
    Safe to call multiple times — creates new snapshot items.
    """
    svc = CalendarService(db)
    return await svc.sync_for_user(
        current_user.id, current_user.tenant_id, months_ahead=months_ahead
    )


@router.post("/items/{item_id}/dismiss", status_code=200)
async def dismiss_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    svc = CalendarService(db)
    item = await svc.dismiss_item(item_id, current_user.id)
    await db.commit()
    return item


@router.post("/items/{item_id}/complete", status_code=200)
async def complete_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    svc = CalendarService(db)
    return await svc.complete_item(item_id, current_user.id)


@router.get("/export/ics")
async def export_ics(
    months_ahead: int = Query(3, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Export calendar items as ICS file for Outlook/Google Calendar import."""
    svc = CalendarService(db)
    items = await svc.get_items(
        current_user.id, current_user.tenant_id,
        include_completed=False, include_dismissed=False,
        limit=500,
    )

    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def ics_date(d) -> str:
        if hasattr(d, 'strftime'):
            return d.strftime("%Y%m%d")
        return str(d).replace("-", "")

    def ics_escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Umay Finance//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Umay - Finansal Takvim",
        "X-WR-TIMEZONE:Europe/Istanbul",
    ]

    for item in items:
        direction = (item.description or "EXPENSE").upper()
        is_income = direction == "INCOME"
        item_type = item.item_type if hasattr(item, 'item_type') else item.get('item_type', '')
        title = item.title if hasattr(item, 'title') else item.get('title', '')
        due_date = item.due_date if hasattr(item, 'due_date') else item.get('due_date')
        amount = item.amount if hasattr(item, 'amount') else item.get('amount', 0)
        currency = item.currency if hasattr(item, 'currency') else item.get('currency', 'TRY')
        item_id = item.id if hasattr(item, 'id') else item.get('id', '')

        emoji = "💚" if is_income else "❤️"
        summary = f"{emoji} {ics_escape(title)}"
        desc = f"Tutar: {currency} {amount}" if amount else ""

        uid = f"{item_id}@umay.finance"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{ics_date(due_date)}",
            f"DTEND;VALUE=DATE:{ics_date(due_date)}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{ics_escape(desc)}",
            f"CATEGORIES:{item_type}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines) + "\r\n"

    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=umay-calendar.ics"},
    )


# ── External Calendar Integrations ────────────────────────────────────────────

@router.get("/integrations")
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """List connected Google/Outlook integrations."""
    svc = ExternalCalendarService(db)
    integrations = await svc.list_integrations(current_user.id)
    google_cfg = await get_oauth_config(db, "google")
    ms_cfg = await get_oauth_config(db, "microsoft")
    return {
        "integrations": integrations,
        "providers": {
            "google": {"configured": bool(google_cfg["client_id"]), "label": "Google Takvim"},
            "microsoft": {"configured": bool(ms_cfg["client_id"]), "label": "Outlook Takvim"},
        },
    }


@router.get("/integrations/credentials")
async def get_credentials(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Get stored OAuth credentials (secrets masked)."""
    google_cfg = await get_oauth_config(db, "google")
    ms_cfg = await get_oauth_config(db, "microsoft")

    def mask(s: str) -> str:
        if not s: return ""
        return s[:6] + "•" * max(0, len(s) - 6)

    return {
        "google_client_id": google_cfg["client_id"],
        "google_client_secret": mask(google_cfg["client_secret"]),
        "google_redirect_uri": google_cfg["redirect_uri"],
        "microsoft_client_id": ms_cfg["client_id"],
        "microsoft_client_secret": mask(ms_cfg["client_secret"]),
        "microsoft_redirect_uri": ms_cfg["redirect_uri"],
        "microsoft_tenant_id": ms_cfg["tenant_id"],
    }


@router.put("/integrations/credentials")
async def save_credentials(
    body: OAuthCredentials,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Save OAuth credentials to system_flags (admin only)."""
    if body.google_client_id:
        await _set_flag(db, "oauth_google_client_id", body.google_client_id)
    if body.google_client_secret and "•" not in body.google_client_secret:
        await _set_flag(db, "oauth_google_client_secret", body.google_client_secret)
    if body.google_redirect_uri:
        await _set_flag(db, "oauth_google_redirect_uri", body.google_redirect_uri)
    if body.microsoft_client_id:
        await _set_flag(db, "oauth_microsoft_client_id", body.microsoft_client_id)
    if body.microsoft_client_secret and "•" not in body.microsoft_client_secret:
        await _set_flag(db, "oauth_microsoft_client_secret", body.microsoft_client_secret)
    if body.microsoft_redirect_uri:
        await _set_flag(db, "oauth_microsoft_redirect_uri", body.microsoft_redirect_uri)
    if body.microsoft_tenant_id:
        await _set_flag(db, "oauth_microsoft_tenant_id", body.microsoft_tenant_id)
    await db.commit()
    return {"saved": True}


@router.get("/integrations/google/connect")
async def google_connect(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Return Google OAuth consent URL (frontend will redirect)."""
    svc = ExternalCalendarService(db)
    state = str(current_user.id)
    auth_url = await svc.google_auth_url(state)
    return {"auth_url": auth_url}


@router.get("/integrations/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback — state contains user_id (no token needed)."""
    try:
        user_id = uuid.UUID(state)
    except ValueError:
        return RedirectResponse(url="/settings?tab=integrations&error=invalid_state")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/settings?tab=integrations&error=user_not_found")
    svc = ExternalCalendarService(db)
    await svc.google_callback(code, user.id, user.tenant_id)
    await svc.sync_all_for_user(user.id, user.tenant_id)
    return RedirectResponse(url="/settings?tab=integrations&connected=google")


@router.get("/integrations/microsoft/connect")
async def microsoft_connect(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Return Microsoft OAuth consent URL (frontend will redirect)."""
    svc = ExternalCalendarService(db)
    state = str(current_user.id)
    auth_url = await svc.microsoft_auth_url(state)
    return {"auth_url": auth_url}


@router.get("/integrations/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle Microsoft OAuth callback — state contains user_id (no token needed)."""
    try:
        user_id = uuid.UUID(state) if state else None
    except ValueError:
        user_id = None
    if not user_id:
        return RedirectResponse(url="/settings?tab=integrations&error=invalid_state")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(url="/settings?tab=integrations&error=user_not_found")
    svc = ExternalCalendarService(db)
    await svc.microsoft_callback(code, user.id, user.tenant_id)
    await svc.sync_all_for_user(user.id, user.tenant_id)
    return RedirectResponse(url="/settings?tab=integrations&connected=microsoft")


@router.delete("/integrations/{provider}", status_code=204)
async def disconnect_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "view")),
):
    """Disconnect a Google or Microsoft integration."""
    svc = ExternalCalendarService(db)
    await svc.disconnect(current_user.id, provider)


@router.post("/integrations/sync", status_code=200)
async def manual_sync_integrations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("calendar", "sync")),
):
    """Manually trigger external calendar sync for current user."""
    svc = ExternalCalendarService(db)
    results = await svc.sync_all_for_user(current_user.id, current_user.tenant_id)
    return {"results": results}
