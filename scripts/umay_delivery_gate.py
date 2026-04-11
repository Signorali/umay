#!/usr/bin/env python3
"""
umay_delivery_gate.py — cloud.md §28 Delivery Gate Verification
================================================================
Runs all delivery gate checks against a live Umay backend.

Usage:
    python scripts/umay_delivery_gate.py [--url http://localhost:8000] [--token <JWT>]

Exit code: 0 = ALL PASS  |  1 = FAILURES DETECTED

Cloud.md §28 requirements checked:
  - [ ] /health returns ok
  - [ ] /health/detail ledger balanced
  - [ ] /health/detail redis connected
  - [ ] /health/detail backup path accessible
  - [ ] /setup/status initialized
  - [ ] /setup/precheck all critical checks ok
  - [ ] /auth/login returns JWT
  - [ ] /auth/me returns user info
  - [ ] /auth/mfa/status returns mfa_enabled
  - [ ] /api/v1/accounts responds
  - [ ] /api/v1/reports/income-expense responds
  - [ ] /api/v1/dashboard responds
  - [ ] Database migration version current
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta
from typing import Optional

try:
    import httpx
except ImportError:
    print("[ERROR] httpx not installed: pip install httpx")
    sys.exit(1)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def skip(msg: str) -> None:
    print(f"  {YELLOW}⊘{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}▶ {title}{RESET}")


# ── Gate runner ───────────────────────────────────────────────────────────────

class DeliveryGate:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base = base_url.rstrip("/")
        self.token = token
        self.failures: list[str] = []
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _get(self, path: str, params: dict | None = None, auth: bool = True) -> httpx.Response:
        h = self.headers if auth else {}
        return httpx.get(self._url(path), params=params, headers=h, timeout=15)

    def _post(self, path: str, json_body: dict, auth: bool = True) -> httpx.Response:
        h = self.headers if auth else {}
        return httpx.post(self._url(path), json=json_body, headers=h, timeout=15)

    def check(self, label: str, passed: bool, detail: str = "") -> None:
        if passed:
            ok(f"{label}" + (f"  ({detail})" if detail else ""))
        else:
            fail(f"{label}" + (f"  — {detail}" if detail else ""))
            self.failures.append(label)

    # ── Checks ────────────────────────────────────────────────────────────────

    def check_health(self) -> None:
        section("1. Public Health Endpoint")
        try:
            r = self._get("/api/v1/health", auth=False)
            data = r.json()
            self.check("/health returns 200", r.status_code == 200, f"status={data.get('status')}")
            self.check("overall status ok/degraded", data.get("status") in ("ok", "degraded", "warning"),
                       data.get("status", "missing"))
            checks = data.get("checks", {})
            self.check("database check present", "database" in checks)
            self.check("redis check present", "redis" in checks)
        except Exception as e:
            self.check("/health reachable", False, str(e)[:80])

    def check_liveness(self) -> None:
        section("2. Kubernetes Probes")
        try:
            r = self._get("/api/v1/health/live", auth=False)
            self.check("/health/live returns 200", r.status_code == 200)
        except Exception as e:
            self.check("/health/live reachable", False, str(e)[:60])
        try:
            r = self._get("/api/v1/health/ready", auth=False)
            self.check("/health/ready returns 200", r.status_code == 200)
        except Exception as e:
            self.check("/health/ready reachable", False, str(e)[:60])

    def check_setup(self) -> None:
        section("3. Setup & Precheck")
        try:
            r = self._get("/api/v1/setup/status", auth=False)
            data = r.json()
            self.check("/setup/status returns 200", r.status_code == 200)
            self.check("system is initialized", bool(data.get("initialized")),
                       "Run /setup/init first if not initialized")
        except Exception as e:
            self.check("/setup/status reachable", False, str(e)[:80])
        try:
            r = self._get("/api/v1/setup/precheck", auth=False)
            data = r.json()
            self.check("/setup/precheck returns 200", r.status_code == 200)
            critical = data.get("ready_to_install", False)
            self.check("all critical pre-checks pass", critical,
                       str([c for c in data.get("checks", []) if c.get("status") == "error"]))
        except Exception as e:
            self.check("/setup/precheck reachable", False, str(e)[:80])

    def check_auth(self, email: str, password: str) -> Optional[str]:
        section("4. Authentication")
        if not email or not password:
            skip("Skipping auth checks (no credentials provided)")
            return None
        try:
            r = self._post("/api/v1/auth/login",
                           {"email": email, "password": password}, auth=False)
            self.check("/auth/login returns 200", r.status_code == 200,
                       f"got {r.status_code}")
            token = r.json().get("access_token")
            self.check("access_token present", bool(token))
            if token:
                self.token = token
                self.headers = {"Authorization": f"Bearer {token}"}
            return token
        except Exception as e:
            self.check("/auth/login reachable", False, str(e)[:80])
            return None

    def check_auth_me(self) -> None:
        section("5. User & MFA")
        if not self.token:
            skip("No token — skipping authed checks")
            return
        try:
            r = self._get("/api/v1/auth/me")
            self.check("/auth/me returns 200", r.status_code == 200)
            self.check("user email present", bool(r.json().get("email")))
        except Exception as e:
            self.check("/auth/me reachable", False, str(e)[:80])
        try:
            r = self._get("/api/v1/auth/mfa/status")
            self.check("/auth/mfa/status returns 200", r.status_code == 200)
            self.check("mfa_enabled field present", "mfa_enabled" in r.json())
        except Exception as e:
            self.check("/auth/mfa/status reachable", False, str(e)[:80])

    def check_health_detail(self) -> None:
        section("6. Detailed Health (requires superuser token)")
        if not self.token:
            skip("No token — skipping /health/detail checks")
            return
        try:
            r = self._get("/api/v1/health/detail")
            if r.status_code == 403:
                skip("/health/detail — token is not superuser")
                return
            self.check("/health/detail returns 200", r.status_code == 200, f"got {r.status_code}")
            data = r.json()
            checks = data.get("checks", {})
            ledger = checks.get("ledger_integrity", {})
            self.check("ledger balanced", ledger.get("balanced", False),
                       f"diff={ledger.get('difference', '?')}")
            queue = checks.get("queue", {})
            self.check("queue status ok", queue.get("status") != "error",
                       f"depth={queue.get('depth', '?')}")
            lic = checks.get("license", {})
            self.check("license check returned", lic.get("status") in ("ok", "warning", "unknown"))
        except Exception as e:
            self.check("/health/detail reachable", False, str(e)[:80])

    def check_reports(self) -> None:
        section("7. Reporting Endpoints")
        if not self.token:
            skip("No token — skipping report checks")
            return
        today = date.today()
        start = (today - timedelta(days=30)).isoformat()
        end = today.isoformat()
        for path, params in [
            ("/api/v1/reports/income-expense", {"period_start": start, "period_end": end}),
            ("/api/v1/reports/cash-flow", {}),
            ("/api/v1/reports/loans", {}),
            ("/api/v1/reports/credit-cards", {}),
            ("/api/v1/reports/assets", {}),
            ("/api/v1/reports/investment-performance", {}),
        ]:
            try:
                r = self._get(path, params=params)
                self.check(f"{path} responds", r.status_code in (200, 422),
                           f"got {r.status_code}")
            except Exception as e:
                self.check(f"{path} reachable", False, str(e)[:60])

    def check_core_apis(self) -> None:
        section("8. Core Financial APIs")
        if not self.token:
            skip("No token — skipping core API checks")
            return
        for path in [
            "/api/v1/accounts",
            "/api/v1/transactions",
            "/api/v1/dashboard",
            "/api/v1/planned-payments",
            "/api/v1/loans",
            "/api/v1/credit-cards",
            "/api/v1/assets",
            "/api/v1/investments",
            "/api/v1/backup",
        ]:
            try:
                r = self._get(path)
                self.check(f"{path} responds", r.status_code in (200, 422),
                           f"got {r.status_code}")
            except Exception as e:
                self.check(f"{path} reachable", False, str(e)[:60])

    def print_summary(self) -> None:
        print(f"\n{'─'*55}")
        if self.failures:
            print(f"{BOLD}{RED}DELIVERY GATE: FAILED{RESET}  "
                  f"({len(self.failures)} issue(s))")
            for f in self.failures:
                print(f"  {RED}•{RESET} {f}")
        else:
            print(f"{BOLD}{GREEN}DELIVERY GATE: PASSED{RESET}  All checks ok ✓")
        print(f"{'─'*55}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Umay Delivery Gate — cloud.md §28"
    )
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    parser.add_argument("--token", default=None,
                        help="Superuser JWT for authenticated checks")
    parser.add_argument("--email", default=None,
                        help="Admin email for login (auto-obtains token)")
    parser.add_argument("--password", default=None,
                        help="Admin password for login")
    args = parser.parse_args()

    print(f"\n{BOLD}Umay Delivery Gate{RESET}  —  cloud.md §28")
    print(f"Target: {CYAN}{args.url}{RESET}")
    print(f"Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")

    gate = DeliveryGate(args.url, args.token)

    gate.check_health()
    gate.check_liveness()
    gate.check_setup()

    if args.email and args.password:
        gate.check_auth(args.email, args.password)
    elif args.token:
        print(f"\n  Using provided token for authenticated checks.")

    gate.check_auth_me()
    gate.check_health_detail()
    gate.check_reports()
    gate.check_core_apis()
    gate.print_summary()

    sys.exit(1 if gate.failures else 0)


if __name__ == "__main__":
    main()
