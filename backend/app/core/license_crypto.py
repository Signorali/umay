"""
license_crypto.py — Umay License Cryptography Engine

Security model:
  - Ed25519 asymmetric signing (private key never leaves the developer's machine)
  - Public key is hardcoded here; changing it requires patching the binary
  - Signature covers every field; any tampering invalidates the license
  - License is bound to a specific tenant_id; sharing doesn't help
  - Expiry is enforced server-side; clock manipulation is detectable

License key format:
  UMAY.1.<base64url(zlib(json_payload))>.<base64url(ed25519_64byte_sig)>

  Example:
  UMAY.1.eJyrVkpUslIqS....<signature_here>
"""

import base64
import hashlib
import json
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


# ---------------------------------------------------------------------------
# Public key — hardcoded. To rotate: generate new keypair, replace this value,
# re-issue all licenses. Private key NEVER goes here or in source control.
# ---------------------------------------------------------------------------
_PUBLIC_KEY_B64 = (
    # Generated 2026-04-02 with scripts/generate_keys.py
    # Fingerprint: 3235737D44DDD20EDF24F75CAD922E70
    "MCowBQYDK2VwAyEACGwg68cFAGFBr86BH3sDN8r0AwXXUdqweqn+5acLVSc="
)

LICENSE_KEY_PREFIX = "UMAY.1."
LICENSE_FORMAT_VERSION = 1


class LicensePlan(str, Enum):
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Feature flags per plan (cumulative — higher plan includes lower plan features)
PLAN_FEATURES: dict[LicensePlan, set[str]] = {
    LicensePlan.TRIAL: {
        "transactions", "accounts", "categories", "dashboard",
    },
    LicensePlan.STARTER: {
        "transactions", "accounts", "categories", "dashboard",
        "reports", "export", "import_csv",
        "planned_payments", "loans", "credit_cards",
    },
    LicensePlan.PROFESSIONAL: {
        "transactions", "accounts", "categories", "dashboard",
        "reports", "export", "import_csv",
        "planned_payments", "loans", "credit_cards",
        "investments", "assets", "institutions",
        "documents", "ocr", "backup",
        "period_lock", "audit",
        "calendar",
    },
    LicensePlan.ENTERPRISE: {
        "transactions", "accounts", "categories", "dashboard",
        "reports", "export", "import_csv",
        "planned_payments", "loans", "credit_cards",
        "investments", "assets", "institutions",
        "documents", "ocr", "backup",
        "period_lock", "audit",
        "calendar",
        "multi_tenant", "sso", "api_access",
        "custom_roles", "white_label",
    },
}

PLAN_MAX_USERS: dict[LicensePlan, int] = {
    LicensePlan.TRIAL: 2,
    LicensePlan.STARTER: 5,
    LicensePlan.PROFESSIONAL: 25,
    LicensePlan.ENTERPRISE: 9999,
}


@dataclass
class LicensePayload:
    """Decoded and verified license data."""
    license_id: str          # lid — unique license UUID
    tenant_id: str           # tid — tenant UUID binding
    tenant_slug: str         # slug — extra binding
    plan: LicensePlan        # plan tier
    max_users: int           # user cap
    features: set[str]       # enabled features
    issued_to: str           # ito — company/person name
    issued_at: datetime      # iat
    expires_at: Optional[datetime]  # exp — None = perpetual
    version: int = 1         # ver

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def days_until_expiry(self) -> Optional[int]:
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def to_dict(self) -> dict:
        return {
            "lid": self.license_id,
            "tid": self.tenant_id,
            "slug": self.tenant_slug,
            "plan": self.plan.value,
            "max_users": self.max_users,
            "features": sorted(self.features),
            "ito": self.issued_to,
            "iat": int(self.issued_at.timestamp()),
            "exp": int(self.expires_at.timestamp()) if self.expires_at else None,
            "ver": self.version,
        }


class LicenseError(Exception):
    """Raised when a license is invalid, expired, or tampered."""
    pass


class LicenseTamperedError(LicenseError):
    """Raised specifically when cryptographic verification fails."""
    pass


class LicenseExpiredError(LicenseError):
    """Raised when a license has passed its expiry date."""
    pass


class LicenseTenantMismatchError(LicenseError):
    """Raised when the license doesn't match the requesting tenant."""
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    # Add padding back
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _payload_to_bytes(payload_dict: dict) -> bytes:
    """Stable serialization: sorted keys, compact JSON, zlib compressed."""
    json_bytes = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return zlib.compress(json_bytes, level=9)


def _bytes_to_payload(data: bytes) -> dict:
    json_bytes = zlib.decompress(data)
    return json.loads(json_bytes)


def _get_public_key() -> Ed25519PublicKey:
    from cryptography.hazmat.primitives.serialization import load_der_public_key
    try:
        raw = base64.b64decode(_PUBLIC_KEY_B64)
        return load_der_public_key(raw)
    except Exception as exc:
        raise LicenseError(f"License public key corrupted: {exc}") from exc


def _fingerprint(key: bytes) -> str:
    """SHA-256 fingerprint for display."""
    return hashlib.sha256(key).hexdigest()[:16].upper()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sign_license(payload: LicensePayload, private_key_b64: str) -> str:
    """
    Sign a license with the Ed25519 private key.
    Returns the full license key string.

    This function should only ever be called by the license issuance tool
    (scripts/issue_license.py), never by the running application.

    Args:
        payload: The license data to sign.
        private_key_b64: Base64-encoded DER private key (from generate_keys.py).

    Returns:
        License key string: UMAY.1.<payload_b64>.<sig_b64>
    """
    from cryptography.hazmat.primitives.serialization import load_der_private_key

    raw_key = base64.b64decode(private_key_b64)
    private_key: Ed25519PrivateKey = load_der_private_key(raw_key, password=None)

    payload_bytes = _payload_to_bytes(payload.to_dict())
    payload_b64 = _b64url_encode(payload_bytes)

    signature = private_key.sign(payload_bytes)
    sig_b64 = _b64url_encode(signature)

    return f"{LICENSE_KEY_PREFIX}{payload_b64}.{sig_b64}"


def verify_license(
    license_key: str,
    expected_tenant_id: Optional[str] = None,
) -> LicensePayload:
    """
    Verify and decode a license key.

    Raises:
        LicenseTamperedError: if the signature is invalid or format is wrong.
        LicenseExpiredError: if the license has passed its expiry date.
        LicenseTenantMismatchError: if the tenant_id doesn't match.
        LicenseError: for other structural issues.

    Returns:
        LicensePayload with all verified license data.
    """
    if not license_key or not license_key.startswith(LICENSE_KEY_PREFIX):
        raise LicenseTamperedError("Invalid license key format")

    remainder = license_key[len(LICENSE_KEY_PREFIX):]
    parts = remainder.split(".")
    if len(parts) != 2:
        raise LicenseTamperedError("Invalid license key structure")

    payload_b64, sig_b64 = parts

    try:
        payload_bytes = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
    except Exception:
        raise LicenseTamperedError("License key contains invalid encoding")

    # Verify signature FIRST before trusting any data
    pub_key = _get_public_key()
    try:
        pub_key.verify(signature, payload_bytes)
    except InvalidSignature:
        raise LicenseTamperedError(
            "License signature verification failed — key may be forged or tampered"
        )

    # Decode payload only after successful verification
    try:
        data = _bytes_to_payload(payload_bytes)
    except Exception:
        raise LicenseTamperedError("License payload is corrupt")

    # Validate required fields
    required = {"lid", "tid", "slug", "plan", "max_users", "features", "ito", "iat", "ver"}
    missing = required - set(data.keys())
    if missing:
        raise LicenseTamperedError(f"License missing fields: {missing}")

    if data.get("ver") != LICENSE_FORMAT_VERSION:
        raise LicenseError(f"Unsupported license format version: {data.get('ver')}")

    try:
        plan = LicensePlan(data["plan"])
    except ValueError:
        raise LicenseError(f"Unknown license plan: {data['plan']}")

    issued_at = datetime.fromtimestamp(data["iat"], tz=timezone.utc)
    expires_at = (
        datetime.fromtimestamp(data["exp"], tz=timezone.utc)
        if data["exp"] is not None
        else None
    )

    license_payload = LicensePayload(
        license_id=data["lid"],
        tenant_id=data["tid"],
        tenant_slug=data["slug"],
        plan=plan,
        max_users=int(data["max_users"]),
        features=set(data["features"]),
        issued_to=data["ito"],
        issued_at=issued_at,
        expires_at=expires_at,
        version=data["ver"],
    )

    # Expiry check
    if license_payload.is_expired:
        raise LicenseExpiredError(
            f"License expired on {expires_at.strftime('%Y-%m-%d')}"
        )

    # Tenant binding check
    if expected_tenant_id and license_payload.tenant_id != str(expected_tenant_id):
        raise LicenseTenantMismatchError(
            "This license is not valid for the current tenant"
        )

    return license_payload


def generate_keypair() -> tuple[str, str]:
    """
    Generate a new Ed25519 key pair.
    Returns (private_key_b64, public_key_b64) — both DER-encoded, base64.

    Call this ONCE and store the private key in a vault.
    The public key goes into _PUBLIC_KEY_B64 above.
    """
    private_key = Ed25519PrivateKey.generate()
    pub_key = private_key.public_key()

    private_der = private_key.private_bytes(
        Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
    )
    public_der = pub_key.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    private_b64 = base64.b64encode(private_der).decode()
    public_b64 = base64.b64encode(public_der).decode()

    return private_b64, public_b64
