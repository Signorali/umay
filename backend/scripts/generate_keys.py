#!/usr/bin/env python3
"""
generate_keys.py — One-time Ed25519 key pair generation for Umay licensing.

Run ONCE in a secure offline environment. Store the private key in a vault
(e.g., 1Password, HashiCorp Vault, AWS Secrets Manager).

The public key goes into: backend/app/core/license_crypto.py → _PUBLIC_KEY_B64

Usage:
    cd backend
    python scripts/generate_keys.py

Output:
    PRIVATE KEY (KEEP SECRET — never commit, never share):
    <base64 DER>

    PUBLIC KEY (paste into license_crypto.py → _PUBLIC_KEY_B64):
    <base64 DER>

    Key fingerprint: ABCD1234...
"""

import sys
import os

# Ensure we can import from the app package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.license_crypto import generate_keypair
import hashlib
import base64


def main():
    private_b64, public_b64 = generate_keypair()

    # Fingerprint from public key bytes
    pub_bytes = base64.b64decode(public_b64)
    fingerprint = hashlib.sha256(pub_bytes).hexdigest()[:32].upper()

    print("=" * 70)
    print("  UMAY LICENSE KEY PAIR — GENERATED")
    print("=" * 70)
    print()
    print(">>> PRIVATE KEY (STORE IN VAULT — NEVER COMMIT TO GIT) <<<")
    print(private_b64)
    print()
    print(">>> PUBLIC KEY (paste into license_crypto.py → _PUBLIC_KEY_B64) <<<")
    print(public_b64)
    print()
    print(f"Key fingerprint: {fingerprint}")
    print()
    print("Next steps:")
    print("  1. Store the PRIVATE KEY in your secrets vault")
    print("  2. Paste the PUBLIC KEY into license_crypto.py → _PUBLIC_KEY_B64")
    print("  3. Delete this terminal output / clear your clipboard")
    print("  4. Run 'python scripts/issue_license.py --help' to issue licenses")
    print("=" * 70)


if __name__ == "__main__":
    main()
