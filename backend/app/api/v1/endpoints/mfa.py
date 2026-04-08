"""MFA endpoints — TOTP setup, confirm, verify, disable (cloud.md §14)."""
from typing import Annotated
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.mfa_service import MfaService

router = APIRouter(prefix="/auth/mfa", tags=["mfa"])


class TotpRequest(BaseModel):
    totp_code: str


# ── GET /auth/mfa/status ─────────────────────────────────────────────────────

@router.get("/status")
async def mfa_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Return MFA enabled state and backup codes remaining count."""
    svc = MfaService(db)
    return await svc.get_status(current_user.id, current_user.tenant_id)


# ── POST /auth/mfa/setup ──────────────────────────────────────────────────────

@router.post("/setup")
async def mfa_setup(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Begin MFA setup: generates TOTP secret + QR code.
    Returns QR as data URL and backup codes (shown ONCE).
    MFA is not active until /mfa/confirm is called.
    """
    svc = MfaService(db)
    return await svc.setup_mfa(current_user.id, current_user.tenant_id)


# ── POST /auth/mfa/confirm ────────────────────────────────────────────────────

@router.post("/confirm")
async def mfa_confirm(
    body: TotpRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Complete MFA setup: verify first TOTP code to activate.
    Call after scanning QR and entering the 6-digit code.
    """
    svc = MfaService(db)
    return await svc.confirm_mfa(current_user.id, current_user.tenant_id, body.totp_code)


# ── POST /auth/mfa/verify ─────────────────────────────────────────────────────

@router.post("/verify")
async def mfa_verify(
    body: TotpRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Verify MFA during login step 2.
    Called after password auth succeeds when MFA is enabled.
    Accepts 6-digit TOTP or 8-char backup code.
    """
    svc = MfaService(db)
    ok = await svc.verify_totp(current_user.id, current_user.tenant_id, body.totp_code)
    return {"verified": ok}


# ── POST /auth/mfa/disable ────────────────────────────────────────────────────

@router.post("/disable")
async def mfa_disable(
    body: TotpRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Disable MFA. Requires current TOTP code as confirmation.
    """
    svc = MfaService(db)
    return await svc.disable_mfa(current_user.id, current_user.tenant_id, body.totp_code)


# ── POST /auth/mfa/backup-codes ───────────────────────────────────────────────

@router.post("/backup-codes")
async def regenerate_backup_codes(
    body: TotpRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Regenerate backup codes (invalidates existing ones). Requires TOTP."""
    svc = MfaService(db)
    return await svc.regenerate_backup_codes(
        current_user.id, current_user.tenant_id, body.totp_code
    )
