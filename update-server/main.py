"""
Umay Update Server
──────────────────
Müşteri lisanslarını doğrular, güncel sürüm bilgisi ve
Docker registry pull token'ı döner.

Endpoints:
  GET  /health             → canlılık kontrolü
  GET  /version            → genel sürüm bilgisi (kimlik doğrulama gerekmez)
  POST /update/check       → lisans doğrula + sürüm bilgisi + registry token döner
"""

import base64
import json
import os
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Yapılandırma ──────────────────────────────────────────────────────────────

# Ed25519 public key (backend/app/core/license_crypto.py ile aynı)
PUBLIC_KEY_B64 = os.environ.get(
    "LICENSE_PUBLIC_KEY",
    "MCowBQYDK2VwAyEACGwg68cFAGFBr86BH3sDN8r0AwXXUdqweqn+5acLVSc=",
)

# Docker registry pull credentials (registry htpasswd ile eşleşmeli)
REGISTRY_PULL_USER = os.environ.get("REGISTRY_PULL_USER", "puller")
REGISTRY_PULL_PASS = os.environ.get("REGISTRY_PULL_PASS", "changeme")
REGISTRY_HOST     = os.environ.get("REGISTRY_HOST", "koken.myqnapcloud.com")

VERSIONS_DIR = Path(__file__).parent / "versions"
LICENSE_PREFIX = "UMAY.1."

# ── Uygulama ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Umay Update Server", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _load_public_key() -> Ed25519PublicKey:
    raw = base64.b64decode(PUBLIC_KEY_B64)
    return load_der_public_key(raw)  # type: ignore


def _b64u_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _verify_license(license_key: str) -> dict:
    """
    Lisansı doğrula ve payload'ı döner.
    Geçersizse HTTPException 403 fırlatır.
    """
    if not license_key.startswith(LICENSE_PREFIX):
        raise HTTPException(status_code=403, detail="Geçersiz lisans formatı")

    parts = license_key[len(LICENSE_PREFIX):].split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=403, detail="Geçersiz lisans formatı")

    payload_b64, sig_b64 = parts
    try:
        payload_bytes = zlib.decompress(_b64u_decode(payload_b64))
        sig_bytes = _b64u_decode(sig_b64)
    except Exception:
        raise HTTPException(status_code=403, detail="Lisans çözümlenemedi")

    pub_key = _load_public_key()
    try:
        pub_key.verify(sig_bytes, payload_bytes)
    except InvalidSignature:
        raise HTTPException(status_code=403, detail="Lisans imzası geçersiz")

    payload = json.loads(payload_bytes)

    # Süre kontrolü
    if payload.get("expires_at"):
        exp = datetime.fromisoformat(payload["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(status_code=403, detail="Lisans süresi dolmuş")

    return payload


def _load_latest_version() -> dict:
    path = VERSIONS_DIR / "latest.json"
    if not path.exists():
        return {"version": "1.0.0", "changelog": []}
    with open(path) as f:
        return json.load(f)


# ── Endpointler ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "server": "umay-update-server"}


@app.get("/version")
async def get_version():
    """Herkese açık: güncel sürüm bilgisi (kimlik doğrulama gerekmez)."""
    return _load_latest_version()


class UpdateCheckRequest(BaseModel):
    license_key: str
    current_version: Optional[str] = None


@app.post("/update/check")
async def update_check(body: UpdateCheckRequest):
    """
    Lisansı doğrula ve güncelleme bilgisi + registry pull token döner.
    """
    payload = _verify_license(body.license_key)
    latest = _load_latest_version()

    current = body.current_version or "0.0.0"
    has_update = _version_gt(latest["version"], current)

    return {
        "valid": True,
        "tenant_id": payload.get("tenant_id"),
        "plan": payload.get("plan"),
        "current_version": current,
        "latest_version": latest["version"],
        "has_update": has_update,
        "changelog": latest.get("changelog", []) if has_update else [],
        # Registry pull credentials (lisans geçerliyse verilir)
        "registry": {
            "host": REGISTRY_HOST,
            "username": REGISTRY_PULL_USER,
            "password": REGISTRY_PULL_PASS,
        },
    }


def _version_gt(a: str, b: str) -> bool:
    """a > b ise True döner (semantic version karşılaştırma)."""
    try:
        return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))
    except Exception:
        return False
