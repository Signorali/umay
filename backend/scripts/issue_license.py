#!/usr/bin/env python3
"""
issue_license.py — Umay License Issuance Tool

Generates a cryptographically signed license key for a specific tenant.
The private key must be provided via environment variable or --private-key flag.

Usage:
    # Set private key via env var (recommended)
    export UMAY_LICENSE_PRIVATE_KEY="<base64 private key from generate_keys.py>"

    python scripts/issue_license.py \\
        --tenant-id  "550e8400-e29b-41d4-a716-446655440000" \\
        --tenant-slug "acme-corp" \\
        --issued-to  "ACME Corporation" \\
        --plan       professional \\
        --max-users  25 \\
        --expires    2027-01-01

    # Perpetual license (no expiry):
    python scripts/issue_license.py ... --no-expiry

    # Enterprise with custom features:
    python scripts/issue_license.py ... --plan enterprise --max-users 999

Output:
    A UMAY.1.* license key string, ready to paste into the tenant's
    admin panel at Settings → License.
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.license_crypto import (
    LicensePayload,
    LicensePlan,
    PLAN_FEATURES,
    PLAN_MAX_USERS,
    sign_license,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Issue a signed Umay license key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--tenant-id",   required=True, help="Tenant UUID")
    parser.add_argument("--tenant-slug", required=True, help="Tenant slug")
    parser.add_argument("--issued-to",   required=True, help="Company/customer name")
    parser.add_argument(
        "--plan",
        required=True,
        choices=[p.value for p in LicensePlan],
        help="License plan",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=None,
        help="User limit (default: plan default)",
    )
    parser.add_argument(
        "--expires",
        default=None,
        help="Expiry date as YYYY-MM-DD (default: 1 year from today)",
    )
    parser.add_argument(
        "--no-expiry",
        action="store_true",
        help="Issue a perpetual license with no expiry date",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Base64 private key (default: $UMAY_LICENSE_PRIVATE_KEY env var)",
    )
    parser.add_argument(
        "--license-id",
        default=None,
        help="Custom license UUID (default: auto-generated)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Resolve private key
    private_key_b64 = args.private_key or os.environ.get("UMAY_LICENSE_PRIVATE_KEY", "")
    if not private_key_b64:
        print(
            "ERROR: Private key not provided.\n"
            "  Set $UMAY_LICENSE_PRIVATE_KEY or use --private-key",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate tenant UUID
    try:
        tenant_uuid = str(uuid.UUID(args.tenant_id))
    except ValueError:
        print(f"ERROR: Invalid tenant UUID: {args.tenant_id}", file=sys.stderr)
        sys.exit(1)

    plan = LicensePlan(args.plan)
    max_users = args.max_users if args.max_users is not None else PLAN_MAX_USERS[plan]
    features = PLAN_FEATURES[plan]
    now = datetime.now(timezone.utc)

    # Expiry
    if args.no_expiry:
        expires_at = None
    elif args.expires:
        try:
            expires_at = datetime.strptime(args.expires, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            print(f"ERROR: Invalid date format: {args.expires} (use YYYY-MM-DD)", file=sys.stderr)
            sys.exit(1)
    else:
        # Default: 1 year
        from datetime import timedelta
        expires_at = now + timedelta(days=365)

    license_id = args.license_id or str(uuid.uuid4())

    payload = LicensePayload(
        license_id=license_id,
        tenant_id=tenant_uuid,
        tenant_slug=args.tenant_slug,
        plan=plan,
        max_users=max_users,
        features=features,
        issued_to=args.issued_to,
        issued_at=now,
        expires_at=expires_at,
        version=1,
    )

    try:
        license_key = sign_license(payload, private_key_b64)
    except Exception as exc:
        print(f"ERROR: Failed to sign license: {exc}", file=sys.stderr)
        sys.exit(1)

    expiry_str = (
        expires_at.strftime("%Y-%m-%d") if expires_at else "PERPETUAL (no expiry)"
    )

    print()
    print("=" * 70)
    print("  UMAY LICENSE KEY — ISSUED")
    print("=" * 70)
    print(f"  License ID  : {license_id}")
    print(f"  Tenant      : {tenant_uuid} ({args.tenant_slug})")
    print(f"  Issued To   : {args.issued_to}")
    print(f"  Plan        : {plan.value.upper()}")
    print(f"  Max Users   : {max_users}")
    print(f"  Issued At   : {now.strftime('%Y-%m-%d')}")
    print(f"  Expires     : {expiry_str}")
    print(f"  Features    : {', '.join(sorted(features))}")
    print()
    print("  LICENSE KEY (give this to the customer):")
    print()
    print(license_key)
    print()
    print("=" * 70)
    print("  Customer pastes this key at: Settings → License → Activate")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
