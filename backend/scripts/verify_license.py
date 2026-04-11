#!/usr/bin/env python3
"""
verify_license.py — Quick license key inspector/verifier.

Usage:
    python scripts/verify_license.py "UMAY.1.eyJ0ZXh0I..."
    echo "UMAY.1...." | python scripts/verify_license.py -
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.license_crypto import (
    verify_license,
    LicenseError,
    LicenseTamperedError,
    LicenseExpiredError,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_license.py <license_key_or_->")
        sys.exit(1)

    key = sys.argv[1]
    if key == "-":
        key = sys.stdin.read().strip()

    print()
    print("Verifying license key...")

    try:
        payload = verify_license(key)
    except LicenseTamperedError as exc:
        print(f"FAIL: TAMPERED/INVALID — {exc}")
        sys.exit(1)
    except LicenseExpiredError as exc:
        print(f"FAIL: EXPIRED — {exc}")
        sys.exit(2)
    except LicenseError as exc:
        print(f"FAIL: {exc}")
        sys.exit(3)

    expiry = (
        payload.expires_at.strftime("%Y-%m-%d")
        if payload.expires_at
        else "PERPETUAL"
    )

    print("VALID LICENSE")
    print("-" * 50)
    print(f"  License ID  : {payload.license_id}")
    print(f"  Tenant ID   : {payload.tenant_id}")
    print(f"  Tenant Slug : {payload.tenant_slug}")
    print(f"  Issued To   : {payload.issued_to}")
    print(f"  Plan        : {payload.plan.value.upper()}")
    print(f"  Max Users   : {payload.max_users}")
    print(f"  Issued At   : {payload.issued_at.strftime('%Y-%m-%d')}")
    print(f"  Expires     : {expiry}")
    if payload.days_until_expiry is not None:
        print(f"  Days Left   : {payload.days_until_expiry}")
    print(f"  Features    : {', '.join(sorted(payload.features))}")
    print()


if __name__ == "__main__":
    main()
