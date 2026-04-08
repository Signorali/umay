"""BackupService — pg_dump, encrypted backup, restore, and verification."""
import uuid
import os
import asyncio
import subprocess
import hashlib
import json
from datetime import datetime, timezone, date
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, status

from app.core.config import settings


def _backup_dir() -> Path:
    p = Path(settings.BACKUP_PATH)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_subprocess(args: list, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a subprocess synchronously (call via asyncio.to_thread)."""
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


class BackupService:
    """
    Orchestrates database backups using pg_dump and optional encryption.

    In production, pg_dump is invoked as a subprocess.
    The backup file + checksum manifest are stored in BACKUP_PATH.
    """

    def __init__(self, session=None):
        """Session is optional — kept for worker compatibility."""
        pass

    async def create_backup(self, actor_id: Optional[uuid.UUID] = None, label: Optional[str] = None) -> dict:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"umay_backup_{ts}.sql"
        backup_path = _backup_dir() / filename
        manifest_path = _backup_dir() / f"{filename}.manifest.json"

        pg_url = settings.DATABASE_URL
        if "+asyncpg" in pg_url:
            pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            result = await asyncio.to_thread(
                _run_subprocess,
                ["pg_dump", pg_url, "-f", str(backup_path), "--no-password"],
                300,
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"pg_dump failed: {result.stderr[:500]}",
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="pg_dump not found. Ensure PostgreSQL client tools are installed in the container.",
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Backup timed out.",
            )

        checksum = _sha256(backup_path)
        size_bytes = backup_path.stat().st_size

        # Optional encryption (cloud.md §8.15)
        encrypted = False
        final_path = backup_path
        if settings.BACKUP_ENCRYPTION_KEY:
            try:
                final_path = await asyncio.to_thread(
                    self._encrypt_file, backup_path, settings.BACKUP_ENCRYPTION_KEY
                )
                backup_path.unlink()  # remove plaintext
                filename = final_path.name
                checksum = _sha256(final_path)
                size_bytes = final_path.stat().st_size
                encrypted = True
            except Exception as enc_err:
                # Encryption failure is non-fatal — keep plaintext backup
                pass

        manifest = {
            "filename": filename,
            "label": label or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": str(actor_id) if actor_id else "system",
            "size_bytes": size_bytes,
            "checksum_sha256": checksum,
            "encrypted": encrypted,
        }
        manifest_path = _backup_dir() / f"{filename}.manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return manifest

    @staticmethod
    def _encrypt_file(input_path: Path, key_str: str) -> Path:
        """Fernet-encrypt a file. Returns path to .enc file."""
        from cryptography.fernet import Fernet
        import base64
        # Derive a valid Fernet key from the config string
        key_bytes = hashlib.sha256(key_str.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        fernet = Fernet(fernet_key)

        plaintext = input_path.read_bytes()
        ciphertext = fernet.encrypt(plaintext)
        enc_path = input_path.with_suffix(input_path.suffix + ".enc")
        enc_path.write_bytes(ciphertext)
        return enc_path

    @staticmethod
    def _decrypt_file(input_path: Path, key_str: str) -> Path:
        """Fernet-decrypt a .enc file. Returns path to decrypted file."""
        from cryptography.fernet import Fernet
        import base64
        key_bytes = hashlib.sha256(key_str.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        fernet = Fernet(fernet_key)

        ciphertext = input_path.read_bytes()
        plaintext = fernet.decrypt(ciphertext)
        dec_path = input_path.with_suffix("")  # strip .enc
        dec_path.write_bytes(plaintext)
        return dec_path


    def list_backups(self) -> List[dict]:
        backup_dir = _backup_dir()
        manifests = sorted(backup_dir.glob("*.manifest.json"), reverse=True)
        result = []
        for m in manifests:
            try:
                result.append(json.loads(m.read_text()))
            except Exception:
                pass
        return result

    def verify_backup(self, filename: str) -> dict:
        backup_path = _backup_dir() / filename
        manifest_path = _backup_dir() / f"{filename}.manifest.json"

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found.")
        if not manifest_path.exists():
            raise HTTPException(status_code=404, detail="Backup manifest not found.")

        manifest = json.loads(manifest_path.read_text())
        current_checksum = _sha256(backup_path)
        valid = current_checksum == manifest["checksum_sha256"]

        return {
            "filename": filename,
            "valid": valid,
            "stored_checksum": manifest["checksum_sha256"],
            "current_checksum": current_checksum,
            "size_bytes": backup_path.stat().st_size,
        }

    async def restore_backup(self, filename: str, actor_id: uuid.UUID) -> dict:
        """
        Restore a backup. DESTRUCTIVE — drops and recreates all data.
        Requires manual superadmin confirmation (caller's responsibility).
        Automatically decrypts encrypted backups if BACKUP_ENCRYPTION_KEY is set.
        """
        backup_path = _backup_dir() / filename
        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup file not found.")

        # Verify integrity before restore (only if manifest exists)
        manifest_path = _backup_dir() / f"{filename}.manifest.json"
        if manifest_path.exists():
            verification = self.verify_backup(filename)
            if not verification["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Backup checksum mismatch. Refusing to restore corrupted backup.",
                )

        # Decrypt if encrypted
        restore_path = backup_path
        decrypted_temp: Optional[Path] = None
        if filename.endswith(".enc") and settings.BACKUP_ENCRYPTION_KEY:
            try:
                decrypted_temp = await asyncio.to_thread(
                    self._decrypt_file, backup_path, settings.BACKUP_ENCRYPTION_KEY
                )
                restore_path = decrypted_temp
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Failed to decrypt backup: {exc}",
                )

        pg_url = settings.DATABASE_URL
        if "+asyncpg" in pg_url:
            pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql://")

        try:
            # Step 1: Drop and recreate the schema to clear existing data
            drop_result = await asyncio.to_thread(
                _run_subprocess,
                ["psql", pg_url, "--no-password", "-c",
                 "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                 "WHERE datname=current_database() AND pid<>pg_backend_pid();"
                 "DROP SCHEMA public CASCADE;"
                 "CREATE SCHEMA public;"
                 "GRANT ALL ON SCHEMA public TO PUBLIC;"],
                60,
            )
            if drop_result.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Schema drop failed: {drop_result.stderr[:300]}",
                )

            # Step 2: Restore from backup file
            result = await asyncio.to_thread(
                _run_subprocess,
                ["psql", pg_url, "--no-password", "-f", str(restore_path)],
                600,
            )
            if result.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Restore failed: {result.stderr[:500]}",
                )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="psql not found. Ensure PostgreSQL client tools are installed.",
            )
        finally:
            # Always clean up decrypted temp file
            if decrypted_temp and decrypted_temp.exists():
                decrypted_temp.unlink()

        return {
            "restored": filename,
            "restored_by": str(actor_id),
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }

    async def purge_transactions(
        self, db, tenant_id: uuid.UUID, date_from: date, date_to: date, actor_id: uuid.UUID
    ) -> dict:
        """
        Soft-delete all transactions in a date range and reverse their effect on account balances.
        """
        from sqlalchemy import select, update
        from app.models.transaction import Transaction, TransactionType
        from app.models.account import Account
        from app.models.ledger import LedgerEntry

        result = await db.execute(
            select(Transaction).where(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.is_deleted == False,
            )
        )
        txs = result.scalars().all()

        affected_accounts: dict = {}  # account_id -> balance delta

        for tx in txs:
            tx_type = str(tx.transaction_type)
            amt = tx.amount or 0

            # Reverse effect of each transaction type on balances
            if tx_type == "INCOME":
                # Was added to target → subtract back
                if tx.target_account_id:
                    affected_accounts[tx.target_account_id] = affected_accounts.get(tx.target_account_id, 0) - amt
            elif tx_type == "EXPENSE":
                # Was taken from source → add back
                if tx.source_account_id:
                    affected_accounts[tx.source_account_id] = affected_accounts.get(tx.source_account_id, 0) + amt
            elif tx_type == "TRANSFER":
                # Was taken from source, added to target → reverse both
                if tx.source_account_id:
                    affected_accounts[tx.source_account_id] = affected_accounts.get(tx.source_account_id, 0) + amt
                if tx.target_account_id:
                    affected_accounts[tx.target_account_id] = affected_accounts.get(tx.target_account_id, 0) - amt

            # Soft-delete ledger entries
            await db.execute(
                update(LedgerEntry)
                .where(LedgerEntry.transaction_id == tx.id)
                .values(is_deleted=True)
            )
            tx.is_deleted = True

        # Apply balance corrections
        for account_id, delta in affected_accounts.items():
            acc_result = await db.execute(
                select(Account).where(Account.id == account_id)
            )
            acc = acc_result.scalar_one_or_none()
            if acc and delta != 0:
                acc.current_balance = (acc.current_balance or 0) + delta

        await db.commit()

        return {
            "purged_count": len(txs),
            "date_from": str(date_from),
            "date_to": str(date_to),
            "purged_by": str(actor_id),
            "purged_at": datetime.now(timezone.utc).isoformat(),
        }
