"""
CSV Import Service — parse and bulk-import transactions and accounts from CSV.

Design rules (cloud.md §22):
  - CSV import is ALWAYS first-class: validate → preview → confirm
  - Import creates DRAFT transactions by default; user confirms individually or in bulk
  - Never auto-confirm: human must review the preview result
  - Errors are per-row, not fatal: return partial success with row-level error details
  - Accounts are matched by name (case-insensitive) or created if missing

Supported CSV formats:
  1. Transactions:
     date, type, amount, currency, description, source_account, target_account, category, reference
  2. Accounts:
     name, type, currency, opening_balance, institution_name, iban, description

"""
import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.account import Account, AccountType
from app.models.category import Category
from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService
from app.core.exceptions import BusinessRuleError


# ─── Column aliases ──────────────────────────────────────────────────────────

TX_COLUMN_MAP = {
    "date": "transaction_date",
    "tarih": "transaction_date",
    "type": "transaction_type",
    "tür": "transaction_type",
    "tur": "transaction_type",
    "amount": "amount",
    "tutar": "amount",
    "currency": "currency",
    "para birimi": "currency",
    "description": "description",
    "açıklama": "description",
    "aciklama": "description",
    "source_account": "source_account",
    "kaynak hesap": "source_account",
    "target_account": "target_account",
    "hedef hesap": "target_account",
    "category": "category",
    "kategori": "category",
    "reference": "reference_number",
    "referans": "reference_number",
    "notes": "notes",
    "notlar": "notes",
}

ACCT_COLUMN_MAP = {
    "name": "name",
    "ad": "name",
    "hesap adı": "name",
    "type": "account_type",
    "tür": "account_type",
    "currency": "currency",
    "para birimi": "currency",
    "opening_balance": "opening_balance",
    "başlangıç bakiyesi": "opening_balance",
    "institution_name": "institution_name",
    "banka": "institution_name",
    "iban": "iban",
    "description": "description",
    "açıklama": "description",
}

TX_TYPE_MAP = {
    "income": "INCOME", "gelir": "INCOME", "giriş": "INCOME",
    "expense": "EXPENSE", "gider": "EXPENSE", "çıkış": "EXPENSE", "cikis": "EXPENSE",
    "transfer": "TRANSFER", "aktarım": "TRANSFER",
}

ACCT_TYPE_MAP = {
    "cash": "CASH", "nakit": "CASH",
    "bank": "BANK", "banka": "BANK",
    "fx": "FX", "döviz": "FX", "doviz": "FX",
    "credit": "CREDIT", "kredi": "CREDIT",
    "credit_card": "CREDIT_CARD", "kredi kartı": "CREDIT_CARD",
    "investment": "INVESTMENT", "yatırım": "INVESTMENT",
    "savings": "SAVINGS", "birikim": "SAVINGS",
    "other": "OTHER", "diğer": "OTHER",
}


# ─── Result types ─────────────────────────────────────────────────────────────

class ImportRowError:
    def __init__(self, row: int, field: str, message: str):
        self.row = row
        self.field = field
        self.message = message

    def dict(self) -> Dict[str, Any]:
        return {"row": self.row, "field": self.field, "message": self.message}


class ImportPreview:
    def __init__(
        self,
        valid_rows: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        total_rows: int,
    ):
        self.valid_rows = valid_rows
        self.errors = errors
        self.total_rows = total_rows

    def dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "valid_count": len(self.valid_rows),
            "error_count": len(self.errors),
            "errors": self.errors,
            "preview": self.valid_rows[:20],  # first 20 valid rows for UI
        }


# ─── Service ──────────────────────────────────────────────────────────────────

class ImportService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.account_repo = AccountRepository(session)
        self.tx_repo = TransactionRepository(session)
        self.ledger = LedgerService(session)
        self.audit = AuditService(session)

    # ── Public: parse CSV ─────────────────────────────────────────────────────

    async def preview_transactions(
        self, csv_bytes: bytes, tenant_id: uuid.UUID
    ) -> ImportPreview:
        """Parse CSV and return preview with validation errors. Does NOT write to DB."""
        rows, errors, headers = self._parse_csv(csv_bytes, TX_COLUMN_MAP, "transactions")
        if not rows and errors:
            return ImportPreview([], [e.dict() for e in errors], 0)

        # Load account map for this tenant
        account_map = await self._load_account_map(tenant_id)
        category_map = await self._load_category_map(tenant_id)

        valid_rows = []
        for i, row in enumerate(rows, start=2):  # row 1 = header
            row_errors, parsed = self._validate_tx_row(row, i, account_map, category_map)
            if row_errors:
                errors.extend(row_errors)
            else:
                valid_rows.append(parsed)

        return ImportPreview(valid_rows, [e.dict() for e in errors], len(rows))

    async def preview_accounts(
        self, csv_bytes: bytes, tenant_id: uuid.UUID
    ) -> ImportPreview:
        """Parse Account CSV and return preview. Does NOT write to DB."""
        rows, errors, _ = self._parse_csv(csv_bytes, ACCT_COLUMN_MAP, "accounts")
        valid_rows = []
        for i, row in enumerate(rows, start=2):
            row_errors, parsed = self._validate_acct_row(row, i)
            if row_errors:
                errors.extend(row_errors)
            else:
                valid_rows.append(parsed)
        return ImportPreview(valid_rows, [e.dict() for e in errors], len(rows))

    async def import_transactions(
        self,
        csv_bytes: bytes,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_email: str,
        status: TransactionStatus = TransactionStatus.DRAFT,
    ) -> Dict[str, Any]:
        """
        Import transactions from CSV.
        All rows are created as DRAFT by default (status param can override).
        Returns summary: created, skipped, errors.
        """
        preview = await self.preview_transactions(csv_bytes, tenant_id)
        if not preview.valid_rows:
            return {
                "created": 0,
                "skipped": len(preview.errors),
                "errors": preview.errors,
            }

        account_map = await self._load_account_map(tenant_id)
        category_map = await self._load_category_map(tenant_id)
        created = 0

        for row in preview.valid_rows:
            tx = Transaction(
                tenant_id=tenant_id,
                transaction_type=TransactionType[row["transaction_type"]],
                status=status,
                amount=Decimal(str(row["amount"])),
                currency=row.get("currency", "TRY"),
                source_account_id=account_map.get(row.get("source_account", "").lower()),
                target_account_id=account_map.get(row.get("target_account", "").lower()),
                category_id=category_map.get(row.get("category", "").lower()),
                transaction_date=row["transaction_date"],
                description=row.get("description"),
                notes=row.get("notes"),
                reference_number=row.get("reference_number"),
            )
            self.session.add(tx)
            await self.session.flush()

            if status == TransactionStatus.CONFIRMED:
                await self.ledger.post_transaction(tx)

            created += 1

        await self.audit.log(
            action="CSV_IMPORT",
            module="transactions",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            after={"created": created, "status": status},
        )

        return {
            "created": created,
            "skipped": len(preview.errors),
            "errors": preview.errors,
        }

    async def import_accounts(
        self,
        csv_bytes: bytes,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        actor_email: str,
    ) -> Dict[str, Any]:
        """Import accounts from CSV. Skips duplicates (same name in same tenant)."""
        preview = await self.preview_accounts(csv_bytes, tenant_id)
        existing_map = await self._load_account_map(tenant_id)
        created = 0
        skipped = 0

        for row in preview.valid_rows:
            name_key = row["name"].lower()
            if name_key in existing_map:
                skipped += 1
                continue

            acct = Account(
                tenant_id=tenant_id,
                name=row["name"],
                account_type=AccountType[row["account_type"]],
                currency=row.get("currency", "TRY"),
                opening_balance=Decimal(str(row.get("opening_balance", 0))),
                current_balance=Decimal(str(row.get("opening_balance", 0))),
                institution_name=row.get("institution_name"),
                iban=row.get("iban"),
                description=row.get("description"),
            )
            self.session.add(acct)
            created += 1

        if created:
            await self.session.flush()
            await self.audit.log(
                action="CSV_IMPORT",
                module="accounts",
                tenant_id=tenant_id,
                actor_id=actor_id,
                actor_email=actor_email,
                after={"created": created},
            )

        return {
            "created": created,
            "skipped": skipped + len(preview.errors),
            "errors": preview.errors,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _parse_csv(
        self, csv_bytes: bytes, col_map: Dict[str, str], import_type: str
    ) -> Tuple[List[Dict[str, str]], List["ImportRowError"], List[str]]:
        """Decode CSV bytes and normalize header names."""
        try:
            text = csv_bytes.decode("utf-8-sig")  # handle BOM from Excel
        except UnicodeDecodeError:
            text = csv_bytes.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return [], [ImportRowError(0, "file", "CSV dosyası boş veya geçersiz")], []

        # Normalize headers
        normalized_headers = {
            h.strip().lower(): col_map.get(h.strip().lower(), h.strip().lower())
            for h in reader.fieldnames
        }

        rows = []
        errors = []
        for i, raw_row in enumerate(reader, start=2):
            row = {normalized_headers[k.strip().lower()]: v.strip()
                   for k, v in raw_row.items() if k}
            rows.append(row)

        return rows, errors, list(normalized_headers.values())

    def _validate_tx_row(
        self,
        row: Dict[str, str],
        row_num: int,
        account_map: Dict[str, uuid.UUID],
        category_map: Dict[str, uuid.UUID],
    ) -> Tuple[List["ImportRowError"], Dict[str, Any]]:
        errors = []
        parsed: Dict[str, Any] = {}

        # Date
        date_val = row.get("transaction_date", "")
        try:
            parsed["transaction_date"] = datetime.strptime(
                date_val, "%Y-%m-%d"
            ).date() if "-" in date_val else datetime.strptime(date_val, "%d.%m.%Y").date()
        except (ValueError, TypeError):
            errors.append(ImportRowError(row_num, "date", f"Geçersiz tarih formatı: '{date_val}'. Beklenen: YYYY-MM-DD veya DD.MM.YYYY"))

        # Type
        type_raw = row.get("transaction_type", "").lower()
        tx_type = TX_TYPE_MAP.get(type_raw)
        if not tx_type:
            errors.append(ImportRowError(row_num, "type", f"Geçersiz işlem türü: '{type_raw}'"))
        else:
            parsed["transaction_type"] = tx_type

        # Amount
        amount_str = row.get("amount", "").replace(",", ".")
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
            parsed["amount"] = amount
        except (InvalidOperation, ValueError):
            errors.append(ImportRowError(row_num, "amount", f"Geçersiz tutar: '{amount_str}'"))

        # Currency
        parsed["currency"] = row.get("currency", "TRY").upper() or "TRY"

        # Accounts — resolve by name
        source = row.get("source_account", "").lower()
        target = row.get("target_account", "").lower()
        parsed["source_account"] = source
        parsed["target_account"] = target

        if tx_type == "INCOME" and not target:
            errors.append(ImportRowError(row_num, "target_account", "INCOME işlemi için hedef hesap gereklidir"))
        if tx_type == "EXPENSE" and not source:
            errors.append(ImportRowError(row_num, "source_account", "EXPENSE işlemi için kaynak hesap gereklidir"))
        if tx_type == "TRANSFER" and (not source or not target):
            errors.append(ImportRowError(row_num, "accounts", "TRANSFER için hem kaynak hem hedef hesap gereklidir"))

        # Validate accounts exist
        if source and source not in account_map:
            errors.append(ImportRowError(row_num, "source_account", f"Hesap bulunamadı: '{source}'"))
        if target and target not in account_map:
            errors.append(ImportRowError(row_num, "target_account", f"Hesap bulunamadı: '{target}'"))

        # Optional fields
        parsed["description"] = row.get("description") or None
        parsed["notes"] = row.get("notes") or None
        parsed["reference_number"] = row.get("reference_number") or None
        cat = row.get("category", "").lower()
        parsed["category"] = cat

        return errors, parsed

    def _validate_acct_row(
        self, row: Dict[str, str], row_num: int
    ) -> Tuple[List["ImportRowError"], Dict[str, Any]]:
        errors = []
        parsed: Dict[str, Any] = {}

        name = row.get("name", "").strip()
        if not name:
            errors.append(ImportRowError(row_num, "name", "Hesap adı boş olamaz"))
        else:
            parsed["name"] = name

        type_raw = row.get("account_type", "").lower()
        acct_type = ACCT_TYPE_MAP.get(type_raw)
        if not acct_type:
            errors.append(ImportRowError(row_num, "type", f"Geçersiz hesap türü: '{type_raw}'"))
        else:
            parsed["account_type"] = acct_type

        balance_str = row.get("opening_balance", "0").replace(",", ".") or "0"
        try:
            parsed["opening_balance"] = Decimal(balance_str)
        except InvalidOperation:
            errors.append(ImportRowError(row_num, "opening_balance", f"Geçersiz bakiye: '{balance_str}'"))

        parsed["currency"] = row.get("currency", "TRY").upper() or "TRY"
        parsed["institution_name"] = row.get("institution_name") or None
        parsed["iban"] = row.get("iban") or None
        parsed["description"] = row.get("description") or None

        return errors, parsed

    async def _load_account_map(self, tenant_id: uuid.UUID) -> Dict[str, uuid.UUID]:
        """Returns {name.lower() -> account_id} for all active accounts in tenant."""
        result = await self.session.execute(
            select(Account.id, Account.name)
            .where(Account.tenant_id == tenant_id, Account.is_deleted == False)
        )
        return {row.name.lower(): row.id for row in result}

    async def _load_category_map(self, tenant_id: uuid.UUID) -> Dict[str, uuid.UUID]:
        """Returns {name.lower() -> category_id} for all categories in tenant."""
        result = await self.session.execute(
            select(Category.id, Category.name)
            .where(Category.tenant_id == tenant_id, Category.is_deleted == False)
        )
        return {row.name.lower(): row.id for row in result}

    async def process_background_import(
        self,
        import_job_id: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Background import processing for large CSV files (cloud.md §20, §22).
        Called by ARQ worker — reads job data from Redis or system flags,
        processes the import, and returns a summary result.

        The import_job_id references a key where the CSV data was temporarily stored.
        For now, this is a stub that reads from a Redis-cached import job.

        Returns:
            {"imported": int, "errors": int, "detail": list}
        """
        from app.core.redis_client import get_redis
        import json as _json

        redis_key = f"import_job:{import_job_id}"
        try:
            redis = await get_redis()
            raw = await redis.get(redis_key)
            if not raw:
                return {
                    "imported": 0,
                    "errors": 1,
                    "detail": [{"error": f"Import job {import_job_id} not found or already processed"}],
                }

            job_data = _json.loads(raw)
            csv_bytes = job_data["csv_data"].encode("latin-1") if isinstance(job_data.get("csv_data"), str) else b""
            import_type = job_data.get("import_type", "transactions")
            actor_email = job_data.get("actor_email", "system@umay")
            as_draft = job_data.get("as_draft", True)

        except Exception as exc:
            return {"imported": 0, "errors": 1, "detail": [{"error": str(exc)}]}

        # Execute the import
        if import_type == "transactions":
            from app.models.transaction import TransactionStatus
            result = await self.import_transactions(
                csv_bytes=csv_bytes,
                tenant_id=tenant_id,
                actor_id=user_id,
                actor_email=actor_email,
                status=TransactionStatus.DRAFT if as_draft else TransactionStatus.CONFIRMED,
            )
        elif import_type == "accounts":
            result = await self.import_accounts(
                csv_bytes=csv_bytes,
                tenant_id=tenant_id,
                actor_id=user_id,
                actor_email=actor_email,
            )
        else:
            result = {"created": 0, "skipped": 0, "errors": [{"error": f"Unknown import type: {import_type}"}]}

        # Clean up Redis key after processing
        try:
            await redis.delete(redis_key)
        except Exception:
            pass

        return {
            "imported": result.get("created", 0),
            "errors": len(result.get("errors", [])),
            "detail": result.get("errors", []),
        }

