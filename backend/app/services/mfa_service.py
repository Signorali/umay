"""
MfaService — TOTP-based Multi-Factor Authentication (cloud.md §14).

Design rules (cloud.md):
  - MFA is opt-in per user, never forced at system level (architecture supports it)
  - Secret stored encrypted in DB; never returned in plain text after setup
  - QR code is returned only during initial setup (one-time)
  - Backup codes: 8 single-use codes, hashed like passwords
  - Login flow: if MFA enabled, access token is NOT issued until TOTP verified
  - MFA disable requires current TOTP verification (prevents lockout)
"""
import pyotp
import qrcode
import io
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.config import settings


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generate_totp_secret() -> str:
    return pyotp.random_base32()


def _make_totp(secret: str, email: str) -> pyotp.TOTP:
    return pyotp.TOTP(secret, name=email, issuer="Umay")


def _generate_qr_data_url(totp: pyotp.TOTP) -> str:
    """Return a data:image/png;base64,... PNG of the TOTP QR code."""
    uri = totp.provisioning_uri()
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def _hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_backup_codes(count: int = 8) -> tuple[List[str], List[str]]:
    """Returns (plain_codes, hashed_codes). Store only hashed."""
    codes = [secrets.token_hex(4).upper() for _ in range(count)]
    hashed = [_hash_backup_code(c) for c in codes]
    return codes, hashed


# ── Service ───────────────────────────────────────────────────────────────────

class MfaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_user(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User:
        q = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_deleted == False,
        )
        user = (await self.db.execute(q)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    async def setup_mfa(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict:
        """
        Step 1: Generate TOTP secret + QR code for the user.
        MFA is NOT yet active — must call confirm_mfa() to activate.
        Returns: { qr_data_url, secret_preview, backup_codes }
        """
        user = await self._get_user(user_id, tenant_id)

        if getattr(user, "mfa_enabled", False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="MFA is already enabled. Disable first to re-setup.",
            )

        secret = _generate_totp_secret()
        totp = _make_totp(secret, user.email)
        qr_url = _generate_qr_data_url(totp)

        plain_codes, hashed_codes = _generate_backup_codes()

        # Store pending secret (not yet active until confirmed)
        user.mfa_secret = secret
        user.mfa_enabled = False
        user.mfa_backup_codes = ",".join(hashed_codes)
        await self.db.commit()

        return {
            "qr_data_url": qr_url,
            "secret": secret,          # shown once for manual entry
            "backup_codes": plain_codes,  # shown once — user must save these
            "message": "Scan the QR code with your authenticator app, then call /mfa/confirm.",
        }

    async def confirm_mfa(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, totp_code: str
    ) -> dict:
        """
        Step 2: Verify first TOTP code to activate MFA.
        """
        user = await self._get_user(user_id, tenant_id)
        secret = getattr(user, "mfa_secret", None)

        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA setup not started. Call /mfa/setup first.",
            )
        if getattr(user, "mfa_enabled", False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="MFA is already active.",
            )

        totp = _make_totp(secret, user.email)
        if not totp.verify(totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid TOTP code. Check your authenticator app and try again.",
            )

        user.mfa_enabled = True
        await self.db.commit()

        return {"message": "MFA activated successfully.", "mfa_enabled": True}

    async def verify_totp(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, totp_code: str
    ) -> bool:
        """
        Login step 2: Verify TOTP during login flow.
        Returns True on success, raises 401 on failure.
        """
        user = await self._get_user(user_id, tenant_id)

        if not getattr(user, "mfa_enabled", False):
            return True  # MFA not enabled → always passes

        secret = getattr(user, "mfa_secret", None)
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MFA secret missing. Contact administrator.",
            )

        totp = _make_totp(secret, user.email)
        if totp.verify(totp_code, valid_window=1):
            return True

        # Check backup codes
        code_hash = _hash_backup_code(totp_code)
        stored = getattr(user, "mfa_backup_codes", "") or ""
        hashed_list = [c for c in stored.split(",") if c]

        if code_hash in hashed_list:
            # Consume the backup code (one-time use)
            hashed_list.remove(code_hash)
            user.mfa_backup_codes = ",".join(hashed_list)
            await self.db.commit()
            return True

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code.",
        )

    async def disable_mfa(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, totp_code: str
    ) -> dict:
        """
        Disable MFA. Requires current TOTP verification.
        """
        user = await self._get_user(user_id, tenant_id)

        if not getattr(user, "mfa_enabled", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled.",
            )

        # Verify identity before disabling
        await self.verify_totp(user_id, tenant_id, totp_code)

        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        await self.db.commit()

        return {"message": "MFA disabled successfully.", "mfa_enabled": False}

    async def get_status(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        user = await self._get_user(user_id, tenant_id)
        codes = getattr(user, "mfa_backup_codes", "") or ""
        remaining = len([c for c in codes.split(",") if c])
        return {
            "mfa_enabled": bool(getattr(user, "mfa_enabled", False)),
            "backup_codes_remaining": remaining,
        }

    async def regenerate_backup_codes(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID, totp_code: str
    ) -> dict:
        """Regenerate backup codes (requires TOTP verification)."""
        await self.verify_totp(user_id, tenant_id, totp_code)
        user = await self._get_user(user_id, tenant_id)

        plain_codes, hashed_codes = _generate_backup_codes()
        user.mfa_backup_codes = ",".join(hashed_codes)
        await self.db.commit()

        return {
            "backup_codes": plain_codes,
            "message": "Backup codes regenerated. Store these securely — they won't be shown again.",
        }
