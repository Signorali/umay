"""
ExportService — CSV/JSON data export and diagnostics package.
"""
import uuid
import csv
import json
import io
import zipfile
import hashlib
from datetime import datetime, timezone, date
from typing import Optional
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.transaction import Transaction, TransactionStatus
from app.models.account import Account
from app.models.category import Category
from app.models.ledger import LedgerEntry


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    # CSV exports
    # ------------------------------------------------------------------ #

    async def export_transactions_csv(
        self,
        tenant_id: uuid.UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        group_id: Optional[uuid.UUID] = None,
    ) -> bytes:
        q = select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.is_deleted == False,
        )
        if date_from:
            q = q.where(Transaction.transaction_date >= date_from)
        if date_to:
            q = q.where(Transaction.transaction_date <= date_to)
        if group_id:
            q = q.where(Transaction.group_id == group_id)
        q = q.order_by(Transaction.transaction_date.desc())

        txs = list((await self.db.execute(q)).scalars().all())

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "date", "type", "amount", "currency",
            "description", "status", "category_id",
            "source_account_id", "destination_account_id", "created_at"
        ])
        for tx in txs:
            writer.writerow([
                str(tx.id), str(tx.transaction_date), tx.transaction_type,
                str(tx.amount), tx.currency, tx.description or "",
                tx.status, str(tx.category_id) if tx.category_id else "",
                str(tx.source_account_id) if tx.source_account_id else "",
                str(tx.destination_account_id) if tx.destination_account_id else "",
                tx.created_at.isoformat(),
            ])
        return output.getvalue().encode("utf-8-sig")

    async def export_accounts_csv(self, tenant_id: uuid.UUID) -> bytes:
        q = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_deleted == False,
        ).order_by(Account.name)
        accounts = list((await self.db.execute(q)).scalars().all())

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "name", "type", "currency",
            "current_balance", "initial_balance", "bank_name", "iban", "is_active"
        ])
        for a in accounts:
            writer.writerow([
                str(a.id), a.name, a.account_type, a.currency,
                str(a.current_balance), str(a.initial_balance),
                a.bank_name or "", a.iban or "", str(a.is_active),
            ])
        return output.getvalue().encode("utf-8-sig")

    # ------------------------------------------------------------------ #
    # Full JSON data export
    # ------------------------------------------------------------------ #

    async def export_tenant_data_json(self, tenant_id: uuid.UUID) -> bytes:
        """Full portable export of all tenant data as JSON."""
        data: dict = {
            "export_info": {
                "tenant_id": str(tenant_id),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "app_version": settings.APP_VERSION,
                "format": "umay-export-v1",
            },
            "accounts": await self._serialize_accounts(tenant_id),
            "categories": await self._serialize_categories(tenant_id),
            "transactions": await self._serialize_transactions(tenant_id),
        }
        return json.dumps(data, indent=2, default=str).encode("utf-8")

    # ------------------------------------------------------------------ #
    # Diagnostics package (ZIP)
    # ------------------------------------------------------------------ #

    async def build_diagnostics_package(self, tenant_id: uuid.UUID) -> bytes:
        """
        Build a ZIP with:
          - health.json  (current system state)
          - db_stats.json (table row counts)
          - export_manifest.json (version + timestamp)
        """
        health = await self._db_health_stats(tenant_id)
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "app_version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "tenant_id": str(tenant_id),
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            zf.writestr("db_stats.json", json.dumps(health, indent=2))
            # Include accounts CSV
            accounts_csv = await self.export_accounts_csv(tenant_id)
            zf.writestr("accounts.csv", accounts_csv.decode("utf-8-sig"))
        buf.seek(0)
        return buf.read()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _serialize_accounts(self, tenant_id: uuid.UUID) -> list:
        q = select(Account).where(Account.tenant_id == tenant_id, Account.is_deleted == False)
        rows = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "id": str(r.id), "name": r.name, "type": r.account_type,
                "currency": r.currency, "balance": str(r.current_balance),
                "bank_name": r.bank_name, "iban": r.iban,
            }
            for r in rows
        ]

    async def _serialize_categories(self, tenant_id: uuid.UUID) -> list:
        q = select(Category).where(Category.tenant_id == tenant_id, Category.is_deleted == False)
        rows = list((await self.db.execute(q)).scalars().all())
        return [{"id": str(r.id), "name": r.name, "type": r.category_type} for r in rows]

    async def _serialize_transactions(self, tenant_id: uuid.UUID) -> list:
        q = select(Transaction).where(
            Transaction.tenant_id == tenant_id, Transaction.is_deleted == False
        ).order_by(Transaction.transaction_date.desc()).limit(10000)
        rows = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "id": str(r.id), "date": str(r.transaction_date),
                "type": r.transaction_type, "amount": str(r.amount),
                "currency": r.currency, "description": r.description,
                "status": r.status,
            }
            for r in rows
        ]

    async def _db_health_stats(self, tenant_id: uuid.UUID) -> dict:
        tables = [
            "accounts", "categories", "transactions", "ledger_entries",
            "planned_payments", "loans", "credit_cards", "documents",
            "assets", "portfolios",
        ]
        stats = {}
        for table in tables:
            try:
                result = await self.db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
                    {"tid": tenant_id}
                )
                stats[table] = result.scalar_one()
            except Exception:
                stats[table] = "N/A"
        return stats
