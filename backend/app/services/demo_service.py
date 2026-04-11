"""
DemoService — seeds realistic but isolated demo data.

Rules:
- All seeds are tagged with their demo_session_id
- Removal deletes only the tracked record IDs
- Never touches real business data
- ~5 records per module as per cloud.md §25
"""
import uuid
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demo import DemoSession
from app.services.audit_service import AuditService


# ------------------------------------------------------------------ #
# Demo seed data definitions
# ------------------------------------------------------------------ #

_ACCOUNT_SEEDS = [
    {"name": "Demo Vadesiz Hesap", "account_type": "CHECKING", "currency": "TRY",
     "current_balance": Decimal("15000.00"), "initial_balance": Decimal("15000.00"),
     "bank_name": "Demo Bankası"},
    {"name": "Demo Tasarruf Hesabı", "account_type": "SAVINGS", "currency": "TRY",
     "current_balance": Decimal("42500.00"), "initial_balance": Decimal("42500.00"),
     "bank_name": "Demo Bankası"},
    {"name": "Demo USD Hesabı", "account_type": "CHECKING", "currency": "USD",
     "current_balance": Decimal("1200.00"), "initial_balance": Decimal("1200.00"),
     "bank_name": "Demo Bankası"},
    {"name": "Demo Nakit", "account_type": "CASH", "currency": "TRY",
     "current_balance": Decimal("2500.00"), "initial_balance": Decimal("2500.00")},
    {"name": "Demo Yatırım Hesabı", "account_type": "INVESTMENT", "currency": "TRY",
     "current_balance": Decimal("85000.00"), "initial_balance": Decimal("85000.00"),
     "bank_name": "Demo Aracı Kurum"},
]

_CATEGORY_SEEDS = [
    {"name": "Demo Market", "category_type": "EXPENSE"},
    {"name": "Demo Ulaşım", "category_type": "EXPENSE"},
    {"name": "Demo Kira", "category_type": "EXPENSE"},
    {"name": "Demo Maaş", "category_type": "INCOME"},
    {"name": "Demo Faiz Geliri", "category_type": "INCOME"},
]


class DemoService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    async def activate_demo(
        self, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> DemoSession:
        # Check if already active
        existing_q = select(DemoSession).where(
            DemoSession.tenant_id == tenant_id,
            DemoSession.is_active == True,
            DemoSession.is_deleted == False,
        )
        existing = (await self.db.execute(existing_q)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A demo session is already active. Remove it before starting a new one.",
            )

        session = DemoSession(
            tenant_id=tenant_id,
            started_by=actor_id,
            is_active=True,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(session)
        await self.db.flush()

        seed_ids: dict = {}

        # Seed accounts
        from app.models.account import Account
        acct_ids = []
        for seed in _ACCOUNT_SEEDS:
            obj = Account(tenant_id=tenant_id, **seed)
            self.db.add(obj)
            await self.db.flush()
            acct_ids.append(str(obj.id))
        seed_ids["accounts"] = acct_ids

        # Seed categories
        from app.models.category import Category
        cat_ids = []
        for seed in _CATEGORY_SEEDS:
            obj = Category(tenant_id=tenant_id, **seed)
            self.db.add(obj)
            await self.db.flush()
            cat_ids.append(str(obj.id))
        seed_ids["categories"] = cat_ids

        # Seed transactions (5 records linking first account + first categories)
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        today = date.today()
        tx_seeds = [
            {"transaction_type": TransactionType.INCOME, "amount": Decimal("12500.00"),
             "description": "Demo Maaş", "transaction_date": today - timedelta(days=20),
             "status": TransactionStatus.CONFIRMED,
             "source_account_id": uuid.UUID(acct_ids[0]),
             "category_id": uuid.UUID(cat_ids[3])},
            {"transaction_type": TransactionType.EXPENSE, "amount": Decimal("4500.00"),
             "description": "Demo Kira Ödemesi", "transaction_date": today - timedelta(days=18),
             "status": TransactionStatus.CONFIRMED,
             "source_account_id": uuid.UUID(acct_ids[0]),
             "category_id": uuid.UUID(cat_ids[2])},
            {"transaction_type": TransactionType.EXPENSE, "amount": Decimal("850.00"),
             "description": "Demo Market Alışverişi", "transaction_date": today - timedelta(days=10),
             "status": TransactionStatus.CONFIRMED,
             "source_account_id": uuid.UUID(acct_ids[0]),
             "category_id": uuid.UUID(cat_ids[0])},
            {"transaction_type": TransactionType.EXPENSE, "amount": Decimal("320.00"),
             "description": "Demo Ulaşım Kartı", "transaction_date": today - timedelta(days=5),
             "status": TransactionStatus.CONFIRMED,
             "source_account_id": uuid.UUID(acct_ids[0]),
             "category_id": uuid.UUID(cat_ids[1])},
            {"transaction_type": TransactionType.INCOME, "amount": Decimal("215.50"),
             "description": "Demo Faiz Geliri", "transaction_date": today - timedelta(days=1),
             "status": TransactionStatus.CONFIRMED,
             "source_account_id": uuid.UUID(acct_ids[1]),
             "category_id": uuid.UUID(cat_ids[4])},
        ]
        tx_ids = []
        for seed in tx_seeds:
            obj = Transaction(tenant_id=tenant_id, currency="TRY", **seed)
            self.db.add(obj)
            await self.db.flush()
            tx_ids.append(str(obj.id))
        seed_ids["transactions"] = tx_ids

        # Update session with seed map
        session.seeded_modules = ",".join(seed_ids.keys())
        session.seed_record_ids = seed_ids

        await self.audit.log(
            actor_id=actor_id, action="demo.activate",
            module="demo", record_id=session.id,
            new_state={"modules": list(seed_ids.keys())},
        )
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def deactivate_demo(
        self, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ) -> dict:
        """Remove all seeded records and close the demo session."""
        session_q = select(DemoSession).where(
            DemoSession.tenant_id == tenant_id,
            DemoSession.is_active == True,
            DemoSession.is_deleted == False,
        )
        session = (await self.db.execute(session_q)).scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="No active demo session found.")

        seed_ids: dict = session.seed_record_ids or {}
        removed: dict = {}

        # Delete in reverse dependency order
        for module, ids in reversed(list(seed_ids.items())):
            count = await self._delete_by_ids(module, [uuid.UUID(i) for i in ids])
            removed[module] = count

        session.is_active = False
        session.ended_at = datetime.now(timezone.utc)

        await self.audit.log(
            actor_id=actor_id, action="demo.deactivate",
            module="demo", record_id=session.id,
            new_state={"removed": removed},
        )
        await self.db.commit()
        return {"removed": removed, "session_id": str(session.id)}

    async def get_status(self, tenant_id: uuid.UUID) -> dict:
        session_q = select(DemoSession).where(
            DemoSession.tenant_id == tenant_id,
            DemoSession.is_active == True,
            DemoSession.is_deleted == False,
        )
        session = (await self.db.execute(session_q)).scalar_one_or_none()
        return {
            "demo_active": session is not None,
            "session_id": str(session.id) if session else None,
            "started_at": session.started_at.isoformat() if session else None,
            "seeded_modules": session.seeded_modules.split(",") if session and session.seeded_modules else [],
        }

    async def _delete_by_ids(self, module: str, ids: list) -> int:
        """Soft-delete seeded records by their IDs."""
        from sqlalchemy import update
        model_map = {
            "transactions": "app.models.transaction.Transaction",
            "accounts": "app.models.account.Account",
            "categories": "app.models.category.Category",
        }
        if module not in model_map or not ids:
            return 0

        module_path, class_name = model_map[module].rsplit(".", 1)
        import importlib
        mod = importlib.import_module(module_path)
        Model = getattr(mod, class_name)

        q = select(Model).where(Model.id.in_(ids))
        rows = list((await self.db.execute(q)).scalars().all())
        for row in rows:
            row.is_deleted = True
        await self.db.flush()
        return len(rows)
