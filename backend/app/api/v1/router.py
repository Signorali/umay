from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, tenants, groups, roles, health, setup,
    permissions,
    accounts, categories, transactions, ledger,
    planned_payments, loans, credit_cards,
    assets, institutions, investments,
    market, obligations, reports, dashboard, backup,
    documents, ocr, calendar,
    demo, system, export,
    import_csv, period_lock, notifications, audit,
    mfa, delete_requests,
    license, transaction_templates, cc_purchase_templates,
    updates,
)

router = APIRouter(prefix="/api/v1")

# Core
router.include_router(health.router, tags=["health"])
router.include_router(setup.router)
router.include_router(auth.router, tags=["auth"])
router.include_router(mfa.router)
router.include_router(users.router)
router.include_router(tenants.router)
router.include_router(groups.router)
router.include_router(roles.router)

# Phase 1 — Permissions
router.include_router(permissions.router)

# Phase 2 — Financial core
router.include_router(accounts.router)
router.include_router(categories.router)
router.include_router(transactions.router)
router.include_router(ledger.router)
router.include_router(planned_payments.router)
router.include_router(loans.router)
router.include_router(credit_cards.router)

# Phase 3 — Advanced finance
router.include_router(assets.router)
router.include_router(institutions.router)
router.include_router(investments.router)
router.include_router(market.router)
router.include_router(obligations.router)
router.include_router(reports.router)
router.include_router(dashboard.router)

# Phase 4 — Documents, OCR, Calendar
router.include_router(documents.router)
router.include_router(ocr.router)
router.include_router(calendar.router)

# Phase 5 — Productization
router.include_router(demo.router)
router.include_router(system.router)
router.include_router(export.router)

# Phase 6 — Import, Period Lock & Notifications
router.include_router(import_csv.router)
router.include_router(period_lock.router)
router.include_router(notifications.router)

# Infrastructure
router.include_router(backup.router)

# Audit trail (read-only, admin)
router.include_router(audit.router)

# Phase 7 — Delete requests
router.include_router(delete_requests.router)

# Licensing
router.include_router(license.router)

# Updates
router.include_router(updates.router)

# Transaction templates
router.include_router(transaction_templates.router)
router.include_router(cc_purchase_templates.router)
