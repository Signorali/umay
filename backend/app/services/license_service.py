"""
license_service.py — Umay License Validation Service

Responsibilities:
  1. Activate a license key for a tenant (verify + persist to DB)
  2. Look up the current license for a tenant (DB → crypto re-verify)
  3. Cache valid license payloads in Redis (1-hour TTL) for fast per-request checks
  4. Provide a dependency-injectable "require_feature" check
  5. Enforce user count limits

Redis key convention:
  license:tenant:<tenant_id>   →  JSON of LicensePayload fields
  license:tenant:<tenant_id>:invalid  →  "1" (license invalidated, short TTL)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

from app.core.license_crypto import (
    LicenseError,
    LicenseExpiredError,
    LicenseTamperedError,
    LicenseTenantMismatchError,
    LicensePayload,
    LicensePlan,
    verify_license,
)
from app.models.license import TenantLicense

log = logging.getLogger(__name__)

_CACHE_TTL = 3600          # 1 hour
_INVALID_CACHE_TTL = 300   # 5 min (don't hammer DB for known-bad licenses)


class LicenseService:

    def __init__(self, session: AsyncSession, redis=None):
        self._session = session
        self._redis = redis  # optional; graceful degradation without Redis

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_key(self, tenant_id: str) -> str:
        return f"license:tenant:{tenant_id}"

    def _invalid_key(self, tenant_id: str) -> str:
        return f"license:tenant:{tenant_id}:invalid"

    async def _cache_set(self, tenant_id: str, payload: LicensePayload) -> None:
        if not self._redis:
            return
        data = {
            "license_id": payload.license_id,
            "tenant_id": payload.tenant_id,
            "tenant_slug": payload.tenant_slug,
            "plan": payload.plan.value,
            "max_users": payload.max_users,
            "features": sorted(payload.features),
            "issued_to": payload.issued_to,
            "issued_at": payload.issued_at.isoformat(),
            "expires_at": payload.expires_at.isoformat() if payload.expires_at else None,
            "version": payload.version,
        }
        await self._redis.setex(self._cache_key(tenant_id), _CACHE_TTL, json.dumps(data))
        # Clear any "invalid" marker
        await self._redis.delete(self._invalid_key(tenant_id))

    async def _cache_get(self, tenant_id: str) -> Optional[LicensePayload]:
        if not self._redis:
            return None
        raw = await self._redis.get(self._cache_key(tenant_id))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return LicensePayload(
                license_id=data["license_id"],
                tenant_id=data["tenant_id"],
                tenant_slug=data["tenant_slug"],
                plan=LicensePlan(data["plan"]),
                max_users=data["max_users"],
                features=set(data["features"]),
                issued_to=data["issued_to"],
                issued_at=datetime.fromisoformat(data["issued_at"]),
                expires_at=(
                    datetime.fromisoformat(data["expires_at"])
                    if data["expires_at"]
                    else None
                ),
                version=data["version"],
            )
        except Exception:
            return None

    async def _cache_invalidate(self, tenant_id: str) -> None:
        if not self._redis:
            return
        await self._redis.delete(self._cache_key(tenant_id))
        await self._redis.setex(self._invalid_key(tenant_id), _INVALID_CACHE_TTL, "1")

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def activate(self, tenant_id: UUID, license_key: str) -> LicensePayload:
        """
        Verify and activate a license key for a tenant.

        - Verifies the Ed25519 signature
        - Checks tenant binding and expiry
        - Upserts the license record in DB
        - Populates Redis cache

        Raises LicenseError subclasses on failure.
        """
        # Cryptographic verification (raises on any issue)
        payload = verify_license(license_key, expected_tenant_id=str(tenant_id))

        # Persist to DB (upsert — one license per tenant)
        existing = await self._get_db_record(tenant_id)
        if existing:
            existing.license_key = license_key
            existing.license_id = payload.license_id
            existing.plan = payload.plan.value
            existing.issued_to = payload.issued_to
            existing.max_users = payload.max_users
            existing.features_json = json.dumps(sorted(payload.features))
            existing.issued_at = payload.issued_at
            existing.expires_at = payload.expires_at
            existing.is_active = True
            existing.last_verified_at = datetime.now(timezone.utc)
        else:
            record = TenantLicense(
                tenant_id=tenant_id,
                license_key=license_key,
                license_id=payload.license_id,
                plan=payload.plan.value,
                issued_to=payload.issued_to,
                max_users=payload.max_users,
                features_json=json.dumps(sorted(payload.features)),
                issued_at=payload.issued_at,
                expires_at=payload.expires_at,
                is_active=True,
                last_verified_at=datetime.now(timezone.utc),
            )
            self._session.add(record)

        await self._session.commit()
        await self._cache_set(str(tenant_id), payload)

        log.info(
            "License activated: tenant=%s plan=%s lid=%s",
            tenant_id,
            payload.plan.value,
            payload.license_id,
        )
        return payload

    async def get_license(self, tenant_id: UUID) -> Optional[LicensePayload]:
        """
        Return the current verified license for a tenant.

        Fast path: Redis cache hit → no DB / crypto overhead.
        Slow path: DB lookup → re-verify signature → repopulate cache.
        Returns None if no license exists or license is invalid/expired.
        """
        tid = str(tenant_id)

        # Check Redis "invalid" marker first (avoid DB hammering)
        if self._redis:
            invalid = await self._redis.get(self._invalid_key(tid))
            if invalid:
                return None

        # Cache hit
        cached = await self._cache_get(tid)
        if cached:
            # Quick expiry check on cached payload
            if cached.is_expired:
                await self._cache_invalidate(tid)
                return None
            return cached

        # Slow path: DB
        record = await self._get_db_record(tenant_id)
        if not record or not record.is_active:
            return None

        try:
            payload = verify_license(record.license_key, expected_tenant_id=tid)
        except (LicenseTamperedError, LicenseExpiredError, LicenseTenantMismatchError) as exc:
            log.warning("License re-verification failed for tenant %s: %s", tid, exc)
            await self._cache_invalidate(tid)
            return None
        except LicenseError as exc:
            log.error("Unexpected license error for tenant %s: %s", tid, exc)
            return None

        # Update last_verified_at without hammering — only if > 1 hour since last
        now = datetime.now(timezone.utc)
        if (
            record.last_verified_at is None
            or (now - record.last_verified_at).total_seconds() > 3600
        ):
            record.last_verified_at = now
            await self._session.commit()

        await self._cache_set(tid, payload)
        return payload

    async def deactivate(self, tenant_id: UUID) -> None:
        """Deactivate the license for a tenant."""
        record = await self._get_db_record(tenant_id)
        if record:
            record.is_active = False
            await self._session.commit()
        await self._cache_invalidate(str(tenant_id))

    async def get_status_dict(self, tenant_id: UUID) -> dict:
        """
        Return a dict suitable for the LicenseStatusResponse schema.
        Safe to call on unlicensed tenants — returns trial status.
        """
        payload = await self.get_license(tenant_id)
        if payload is None:
            # Trial süresi kontrolü
            trial_expired = False
            days_left = None
            trial_expires_at = None
            tenant_row = await self._session.execute(
                select(Tenant.trial_expires_at).where(Tenant.id == str(tenant_id))
            )
            trial_expires_at = tenant_row.scalar_one_or_none()
            if trial_expires_at:
                now = datetime.now(timezone.utc)
                if trial_expires_at.tzinfo is None:
                    trial_expires_at = trial_expires_at.replace(tzinfo=timezone.utc)
                delta = (trial_expires_at - now).days
                days_left = max(delta, 0)
                trial_expired = now > trial_expires_at

            return {
                "is_licensed": False,
                "plan": "trial",
                "issued_to": "",
                "max_users": 2,
                "features": [] if trial_expired else ["transactions", "accounts", "categories", "dashboard"],
                "issued_at": None,
                "expires_at": trial_expires_at,
                "days_until_expiry": days_left,
                "is_expired": trial_expired,
                "license_id": None,
            }
        return {
            "is_licensed": True,
            "plan": payload.plan.value,
            "issued_to": payload.issued_to,
            "max_users": payload.max_users,
            "features": sorted(payload.features),
            "issued_at": payload.issued_at,
            "expires_at": payload.expires_at,
            "days_until_expiry": payload.days_until_expiry,
            "is_expired": payload.is_expired,
            "license_id": payload.license_id,
        }

    # ------------------------------------------------------------------
    # Authorization helpers (used as FastAPI dependencies)
    # ------------------------------------------------------------------

    async def check_feature(self, tenant_id: UUID, feature: str) -> bool:
        """Return True if the tenant's license includes the given feature."""
        payload = await self.get_license(tenant_id)
        if payload is None:
            # Trial mode: only basic features allowed
            from app.core.license_crypto import PLAN_FEATURES, LicensePlan
            return feature in PLAN_FEATURES[LicensePlan.TRIAL]
        return payload.has_feature(feature)

    async def check_user_limit(self, tenant_id: UUID, current_user_count: int) -> bool:
        """Return True if adding another user stays within the license cap."""
        payload = await self.get_license(tenant_id)
        max_users = payload.max_users if payload else 2  # trial limit
        return current_user_count < max_users

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_db_record(self, tenant_id: UUID) -> Optional[TenantLicense]:
        result = await self._session.execute(
            select(TenantLicense).where(
                TenantLicense.tenant_id == tenant_id,
                TenantLicense.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
