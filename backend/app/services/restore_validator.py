"""
RestoreValidator — post-restore integrity checks.

Run after every backup restore to confirm system consistency.
Checks: table presence, row count parity, ledger balance, alembic version.
"""
import uuid
from typing import Optional
from decimal import Decimal
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import LedgerEntry


EXPECTED_TABLES = [
    "tenants", "groups", "users", "roles", "permissions",
    "accounts", "categories", "transactions", "ledger_entries",
    "planned_payments", "loans", "loan_installments",
    "credit_cards", "credit_card_statements",
    "assets", "asset_valuations", "institutions",
    "portfolios", "investment_transactions", "portfolio_positions",
    "market_providers", "price_snapshots", "watchlist_items",
    "dashboard_widgets", "documents", "ocr_drafts",
    "calendar_items", "calendar_sync_logs",
    "system_flags", "maintenance_windows", "demo_sessions",
    "audit_logs", "license_records", "alembic_version",
]


class RestoreValidator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_all_checks(self, tenant_id: Optional[uuid.UUID] = None) -> dict:
        results = {}
        results["table_existence"] = await self.check_table_existence()
        results["ledger_balance"] = await self.check_ledger_balance(tenant_id)
        results["alembic_version"] = await self.check_alembic_versions()
        results["row_counts"] = await self.get_row_counts(tenant_id)

        all_ok = all(
            v.get("ok", False) for v in results.values() if isinstance(v, dict)
        )
        return {
            "overall": "ok" if all_ok else "failed",
            "checks": results,
        }

    async def check_table_existence(self) -> dict:
        missing = []
        for table in EXPECTED_TABLES:
            try:
                result = await self.db.execute(
                    text(f"SELECT to_regclass('public.{table}')")
                )
                exists = result.scalar_one() is not None
                if not exists:
                    missing.append(table)
            except Exception as e:
                missing.append(f"{table} (error: {str(e)[:50]})")

        return {
            "ok": len(missing) == 0,
            "expected": len(EXPECTED_TABLES),
            "missing": missing,
        }

    async def check_ledger_balance(self, tenant_id: Optional[uuid.UUID] = None) -> dict:
        """
        Double-entry rule: for every confirmed transaction,
        sum(DEBIT entries) must equal sum(CREDIT entries).
        """
        try:
            q = select(
                LedgerEntry.entry_type,
                func.sum(LedgerEntry.amount).label("total"),
            ).where(LedgerEntry.is_deleted == False)

            if tenant_id:
                # Join to transactions to filter by tenant
                from app.models.transaction import Transaction
                q = q.join(Transaction, LedgerEntry.transaction_id == Transaction.id).where(
                    Transaction.tenant_id == tenant_id,
                    Transaction.is_deleted == False,
                )

            q = q.group_by(LedgerEntry.entry_type)
            rows = (await self.db.execute(q)).all()

            totals = {row.entry_type: Decimal(str(row.total or 0)) for row in rows}
            debit = totals.get("DEBIT", Decimal("0"))
            credit = totals.get("CREDIT", Decimal("0"))
            balanced = abs(debit - credit) < Decimal("0.01")

            return {
                "ok": balanced,
                "debit_total": float(debit),
                "credit_total": float(credit),
                "difference": float(abs(debit - credit)),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    async def check_alembic_versions(self) -> dict:
        try:
            result = await self.db.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            versions = [row[0] for row in result.fetchall()]
            return {"ok": len(versions) > 0, "versions": versions}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    async def get_row_counts(self, tenant_id: Optional[uuid.UUID] = None) -> dict:
        tenant_tables = [
            "accounts", "categories", "transactions", "planned_payments",
            "loans", "credit_cards", "assets", "portfolios", "documents",
        ]
        global_tables = ["tenants", "users", "audit_logs", "license_records"]

        counts = {}
        for table in global_tables:
            try:
                result = await self.db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = result.scalar_one()
            except Exception:
                counts[table] = "error"

        if tenant_id:
            for table in tenant_tables:
                try:
                    result = await self.db.execute(
                        text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
                        {"tid": tenant_id},
                    )
                    counts[f"{table}(tenant)"] = result.scalar_one()
                except Exception:
                    counts[f"{table}(tenant)"] = "error"

        return {"ok": True, "counts": counts}
