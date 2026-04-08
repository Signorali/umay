"""
ExternalCalendarService — OAuth2 sync with Google Calendar and Microsoft Outlook.

Flow:
  1. User clicks "Bağla" → frontend redirects to /calendar/integrations/{provider}/connect
  2. Backend redirects to Google/Microsoft OAuth consent page
  3. After consent, provider redirects back to /calendar/integrations/{provider}/callback
  4. Backend exchanges code for tokens, stores in calendar_integrations table
  5. Worker calls sync_external_calendars() every 15 min for all active integrations
"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.calendar_integration import CalendarIntegration
from app.models.calendar_sync import CalendarItem, CalendarItemType
from app.models.system_meta import SystemFlag

logger = logging.getLogger(__name__)

# ── DB-stored OAuth credential helpers ────────────────────────────────────────

async def _get_flag(db: AsyncSession, key: str) -> Optional[str]:
    q = select(SystemFlag).where(SystemFlag.flag_key == key)
    flag = (await db.execute(q)).scalar_one_or_none()
    return flag.flag_value if flag else None


async def _set_flag(db: AsyncSession, key: str, value: str) -> None:
    q = select(SystemFlag).where(SystemFlag.flag_key == key)
    flag = (await db.execute(q)).scalar_one_or_none()
    if flag:
        flag.flag_value = value
    else:
        flag = SystemFlag(flag_key=key, flag_value=value)
        db.add(flag)
    await db.flush()


async def get_oauth_config(db: AsyncSession, provider: str) -> dict:
    """Return OAuth credentials stored in system_flags (set via Settings UI)."""
    client_id = await _get_flag(db, f"oauth_{provider}_client_id") or ""
    client_secret = await _get_flag(db, f"oauth_{provider}_client_secret") or ""
    redirect_uri = await _get_flag(db, f"oauth_{provider}_redirect_uri") or ""
    tenant_id = await _get_flag(db, "oauth_microsoft_tenant_id") or "common"
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "tenant_id": tenant_id,
    }


def _is_income(item: CalendarItem) -> bool:
    return (item.description or "").upper() == "INCOME"


def _ical_dt(d) -> str:
    """Convert date to iCalendar DATE string."""
    if hasattr(d, 'strftime'):
        return d.strftime("%Y%m%d")
    return str(d).replace("-", "")


class ExternalCalendarService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Token helpers ──────────────────────────────────────────────────────

    async def get_integration(self, user_id: uuid.UUID, provider: str) -> Optional[CalendarIntegration]:
        q = select(CalendarIntegration).where(
            CalendarIntegration.user_id == user_id,
            CalendarIntegration.provider == provider,
            CalendarIntegration.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_integrations(self, user_id: uuid.UUID) -> list:
        q = select(CalendarIntegration).where(
            CalendarIntegration.user_id == user_id,
            CalendarIntegration.is_deleted == False,
        )
        rows = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "provider": r.provider,
                "email": r.email,
                "is_active": r.is_active,
                "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
                "sync_error": r.sync_error,
            }
            for r in rows
        ]

    async def disconnect(self, user_id: uuid.UUID, provider: str):
        integ = await self.get_integration(user_id, provider)
        if integ:
            integ.is_deleted = True
            await self.db.commit()

    # ── Google OAuth ───────────────────────────────────────────────────────

    async def google_auth_url(self, state: str) -> str:
        from google_auth_oauthlib.flow import Flow
        cfg = await get_oauth_config(self.db, "google")
        if not cfg["client_id"] or not cfg["client_secret"]:
            raise HTTPException(status_code=501, detail="Google OAuth yapılandırılmamış. Ayarlar → Entegrasyonlar sayfasından Client ID ve Secret girin.")
        flow = Flow.from_client_config(
            {"web": {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [cfg["redirect_uri"]],
            }},
            scopes=["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/userinfo.email", "openid"],
        )
        flow.redirect_uri = cfg["redirect_uri"]
        auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state, prompt="consent")
        return auth_url

    async def google_callback(
        self, code: str, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CalendarIntegration:
        from google_auth_oauthlib.flow import Flow

        cfg = await get_oauth_config(self.db, "google")
        flow = Flow.from_client_config(
            {"web": {
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [cfg["redirect_uri"]],
            }},
            scopes=["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/userinfo.email", "openid"],
        )
        flow.redirect_uri = cfg["redirect_uri"]
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Get user email
        from googleapiclient.discovery import build
        service = build("oauth2", "v2", credentials=creds)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email", "")

        # Upsert integration
        integ = await self.get_integration(user_id, "google")
        if not integ:
            integ = CalendarIntegration(
                tenant_id=tenant_id,
                user_id=user_id,
                provider="google",
            )
            self.db.add(integ)

        integ.access_token = creds.token
        integ.refresh_token = creds.refresh_token or integ.refresh_token
        integ.token_expires_at = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None
        integ.email = email
        integ.is_active = True
        integ.is_deleted = False
        integ.sync_error = None
        await self.db.commit()
        await self.db.refresh(integ)
        return integ

    async def _get_google_credentials(self, integ: CalendarIntegration):
        """Return valid Google credentials, refreshing token if needed."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        cfg = await get_oauth_config(self.db, "google")
        creds = Credentials(
            token=integ.access_token,
            refresh_token=integ.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg["client_id"],
            client_secret=cfg["client_secret"],
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            integ.access_token = creds.token
            if creds.expiry:
                integ.token_expires_at = creds.expiry.replace(tzinfo=timezone.utc)
            await self.db.commit()
        return creds

    async def sync_google(self, integ: CalendarIntegration, items: list) -> int:
        """Push/update Umay calendar items to Google Calendar."""
        from googleapiclient.discovery import build

        creds = await self._get_google_credentials(integ)
        service = build("calendar", "v3", credentials=creds)
        cal_id = integ.calendar_id or "primary"

        synced = 0
        for item in items:
            income = _is_income(item)
            emoji = "💚" if income else "❤️"
            title = f"{emoji} {item.title}"
            amount_str = f"{item.currency or 'TRY'} {float(item.amount or 0):,.2f}" if item.amount else ""
            date_str = _ical_dt(item.due_date)

            event = {
                "summary": title,
                "description": amount_str,
                "start": {"date": item.due_date.isoformat() if hasattr(item.due_date, 'isoformat') else str(item.due_date)},
                "end": {"date": item.due_date.isoformat() if hasattr(item.due_date, 'isoformat') else str(item.due_date)},
                "extendedProperties": {
                    "private": {
                        "umay_item_id": str(item.id),
                        "umay_item_type": str(item.item_type),
                    }
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": 1440}],  # 1 day before
                },
            }
            try:
                # Check if event already exists via extendedProperties search
                existing = service.events().list(
                    calendarId=cal_id,
                    privateExtendedProperty=f"umay_item_id={item.id}",
                ).execute()

                if existing.get("items"):
                    ev_id = existing["items"][0]["id"]
                    service.events().patch(calendarId=cal_id, eventId=ev_id, body=event).execute()
                else:
                    service.events().insert(calendarId=cal_id, body=event).execute()
                synced += 1
            except Exception as e:
                logger.warning(f"Google Calendar event error for item {item.id}: {e}")

        return synced

    # ── Microsoft OAuth ────────────────────────────────────────────────────

    async def microsoft_auth_url(self, state: str) -> str:
        import msal
        cfg = await get_oauth_config(self.db, "microsoft")
        if not cfg["client_id"] or not cfg["client_secret"]:
            raise HTTPException(status_code=501, detail="Microsoft OAuth yapılandırılmamış. Ayarlar → Entegrasyonlar sayfasından Client ID ve Secret girin.")
        app = msal.ConfidentialClientApplication(
            cfg["client_id"],
            authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
            client_credential=cfg["client_secret"],
        )
        return app.get_authorization_request_url(
            scopes=["Calendars.ReadWrite", "User.Read", "offline_access"],
            redirect_uri=cfg["redirect_uri"],
            state=state,
        )

    async def microsoft_callback(
        self, code: str, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CalendarIntegration:
        import msal, httpx

        cfg = await get_oauth_config(self.db, "microsoft")
        app = msal.ConfidentialClientApplication(
            cfg["client_id"],
            authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
            client_credential=cfg["client_secret"],
        )
        result = app.acquire_token_by_authorization_code(
            code,
            scopes=["Calendars.ReadWrite", "User.Read", "offline_access"],
            redirect_uri=cfg["redirect_uri"],
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Microsoft OAuth error: {result.get('error_description')}")

        access_token = result["access_token"]
        refresh_token = result.get("refresh_token")
        expires_in = result.get("expires_in", 3600)

        # Get user email via Graph API
        async with httpx.AsyncClient() as client:
            me_resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        email = me_resp.json().get("mail") or me_resp.json().get("userPrincipalName", "")

        integ = await self.get_integration(user_id, "microsoft")
        if not integ:
            integ = CalendarIntegration(
                tenant_id=tenant_id,
                user_id=user_id,
                provider="microsoft",
            )
            self.db.add(integ)

        integ.access_token = access_token
        integ.refresh_token = refresh_token or integ.refresh_token
        integ.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        integ.email = email
        integ.is_active = True
        integ.is_deleted = False
        integ.sync_error = None
        await self.db.commit()
        await self.db.refresh(integ)
        return integ

    async def _get_microsoft_token(self, integ: CalendarIntegration) -> str:
        """Return valid Microsoft access token, refreshing if needed."""
        now = datetime.now(timezone.utc)
        expires = integ.token_expires_at
        if expires and expires > now + timedelta(minutes=5):
            return integ.access_token  # type: ignore

        if not integ.refresh_token:
            raise HTTPException(status_code=401, detail="Microsoft token expired, reconnect required.")

        import msal
        cfg = await get_oauth_config(self.db, "microsoft")
        app = msal.ConfidentialClientApplication(
            cfg["client_id"],
            authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
            client_credential=cfg["client_secret"],
        )
        result = app.acquire_token_by_refresh_token(
            integ.refresh_token,
            scopes=["Calendars.ReadWrite", "User.Read", "offline_access"],
        )
        if "error" in result:
            raise HTTPException(status_code=401, detail="Microsoft token refresh failed, reconnect required.")

        integ.access_token = result["access_token"]
        integ.refresh_token = result.get("refresh_token", integ.refresh_token)
        integ.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=result.get("expires_in", 3600))
        await self.db.commit()
        return integ.access_token  # type: ignore

    async def sync_microsoft(self, integ: CalendarIntegration, items: list) -> int:
        """Push/update Umay calendar items to Outlook Calendar via Graph API."""
        import httpx

        token = await self._get_microsoft_token(integ)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        synced = 0

        for item in items:
            income = _is_income(item)
            emoji = "💚" if income else "❤️"
            title = f"{emoji} {item.title}"
            amount_str = f"{item.currency or 'TRY'} {float(item.amount or 0):,.2f}" if item.amount else ""
            date_iso = item.due_date.isoformat() if hasattr(item.due_date, 'isoformat') else str(item.due_date)

            body = {
                "subject": title,
                "body": {"contentType": "text", "content": amount_str},
                "start": {"dateTime": f"{date_iso}T09:00:00", "timeZone": "Europe/Istanbul"},
                "end": {"dateTime": f"{date_iso}T10:00:00", "timeZone": "Europe/Istanbul"},
                "isAllDay": False,
                "isReminderOn": True,
                "reminderMinutesBeforeStart": 1440,
                "categories": [str(item.item_type)],
                "singleValueExtendedProperties": [
                    {"id": "String {00020329-0000-0000-C000-000000000046} Name umay_item_id", "value": str(item.id)}
                ],
            }

            async with httpx.AsyncClient() as client:
                try:
                    # Search for existing event
                    search = await client.get(
                        f"https://graph.microsoft.com/v1.0/me/events?$filter=subject eq '{title}'&$top=5",
                        headers=headers,
                    )
                    existing = [
                        e for e in search.json().get("value", [])
                        if title in e.get("subject", "")
                    ]
                    # Simple match by title+date
                    match = next((
                        e for e in existing
                        if date_iso in (e.get("start", {}).get("dateTime", ""))
                    ), None)

                    if match:
                        await client.patch(
                            f"https://graph.microsoft.com/v1.0/me/events/{match['id']}",
                            headers=headers, json=body,
                        )
                    else:
                        await client.post(
                            "https://graph.microsoft.com/v1.0/me/events",
                            headers=headers, json=body,
                        )
                    synced += 1
                except Exception as e:
                    logger.warning(f"Microsoft Calendar event error for item {item.id}: {e}")

        return synced

    # ── Main sync ──────────────────────────────────────────────────────────

    async def sync_all_for_user(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Sync all active integrations for a user. Called by background worker."""
        from app.models.calendar_sync import CalendarItem

        # Get pending calendar items
        from sqlalchemy import select as sa_select
        from datetime import date
        today = date.today()
        q = sa_select(CalendarItem).where(
            CalendarItem.user_id == user_id,
            CalendarItem.is_completed == False,
            CalendarItem.is_dismissed == False,
            CalendarItem.is_deleted == False,
            CalendarItem.due_date >= today,
        )
        items = list((await self.db.execute(q)).scalars().all())

        if not items:
            return {"synced": 0}

        q2 = sa_select(CalendarIntegration).where(
            CalendarIntegration.user_id == user_id,
            CalendarIntegration.is_active == True,
            CalendarIntegration.is_deleted == False,
        )
        integrations = list((await self.db.execute(q2)).scalars().all())

        results = {}
        for integ in integrations:
            try:
                if integ.provider == "google":
                    count = await self.sync_google(integ, items)
                elif integ.provider == "microsoft":
                    count = await self.sync_microsoft(integ, items)
                else:
                    continue
                integ.last_synced_at = datetime.now(timezone.utc)
                integ.sync_error = None
                results[integ.provider] = count
            except Exception as e:
                integ.sync_error = str(e)[:500]
                logger.error(f"External calendar sync failed [{integ.provider}] user={user_id}: {e}")
                results[integ.provider] = f"error: {e}"

        await self.db.commit()
        return results
