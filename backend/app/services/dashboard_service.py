"""DashboardService — aggregates all widget data into a single response."""
import uuid
from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.dashboard import DashboardRepository
from app.services.report_service import ReportService
from app.services.market_service import MarketService
from app.models.dashboard import WidgetType

# Default widget layout for new users
DEFAULT_WIDGETS = [
    {"widget_type": WidgetType.ACCOUNT_SUMMARY,      "title": "Hesaplar",           "position": 0, "col_span": 2},
    {"widget_type": WidgetType.INCOME_EXPENSE,       "title": "Gelir / Gider",       "position": 1, "col_span": 2},
    {"widget_type": WidgetType.RECENT_TRANSACTIONS,  "title": "Son İşlemler",        "position": 2, "col_span": 2},
    {"widget_type": WidgetType.PLANNED_PAYMENTS,     "title": "Bekleyen Ödemeler",   "position": 3, "col_span": 1},
    {"widget_type": WidgetType.LOAN_SUMMARY,         "title": "Krediler",            "position": 4, "col_span": 1},
    {"widget_type": WidgetType.CARD_DUE,             "title": "Kredi Kartları",      "position": 5, "col_span": 1},
    {"widget_type": WidgetType.MARKET_SYMBOLS,       "title": "Piyasalar",           "position": 6, "col_span": 1},
]


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DashboardRepository(db)
        self.report_svc = ReportService(db)
        self.market_svc = MarketService(db)

    async def get_dashboard(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        group_ids: Optional[List[uuid.UUID]] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> dict:
        # Ensure user has widgets
        widgets = await self.repo.bulk_upsert_defaults(tenant_id, user_id, [
            w.copy() for w in DEFAULT_WIDGETS
        ])
        await self.db.commit()

        # Default period: current month
        today = date.today()
        if not period_start:
            period_start = today.replace(day=1)
        if not period_end:
            period_end = today

        data: dict = {}
        for widget in widgets:
            wtype = widget.widget_type
            cfg = widget.config or {}

            try:
                if wtype == WidgetType.INCOME_EXPENSE:
                    data[wtype] = await self.report_svc.income_expense_report(
                        tenant_id, period_start, period_end, group_ids=group_ids
                    )
                elif wtype == WidgetType.PLANNED_PAYMENTS:
                    data[wtype] = await self.report_svc.cash_flow_projection(
                        tenant_id, months_ahead=cfg.get("months_ahead", 1),
                        group_ids=group_ids
                    )
                elif wtype == WidgetType.LOAN_SUMMARY:
                    data[wtype] = await self.report_svc.loan_report(tenant_id, group_ids=group_ids)
                elif wtype == WidgetType.CARD_DUE:
                    data[wtype] = await self.report_svc.credit_card_report(tenant_id, group_ids=group_ids)
                elif wtype == WidgetType.MARKET_SYMBOLS:
                    symbols = cfg.get("symbols", ["USDTRY", "EURTRY", "XAUUSD"])
                    data[wtype] = await self.market_svc.get_prices(symbols)
                elif wtype == WidgetType.RECENT_TRANSACTIONS:
                    data[wtype] = await self._get_recent_transactions(tenant_id, group_ids=group_ids)
                elif wtype == WidgetType.ACCOUNT_SUMMARY:
                    data[wtype] = await self._get_account_summary(tenant_id, group_ids=group_ids)
                else:
                    data[wtype] = {}
            except Exception:
                data[wtype] = {"error": "widget_data_unavailable"}

        return {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "period": {"start": str(period_start), "end": str(period_end)},
            "widgets": [
                {
                    "id": str(w.id),
                    "type": w.widget_type,
                    "title": w.title,
                    "position": w.position,
                    "col_span": w.col_span,
                    "row_span": w.row_span,
                    "data": data.get(w.widget_type, {}),
                }
                for w in widgets
            ],
            # Flat summary keys for frontend DashboardPage compatibility
            "summary": self._extract_summary(data),
            "recent_transactions": self._extract_recent_transactions(data),
            "upcoming_payments": self._extract_upcoming_payments(data),
        }

    def _extract_summary(self, data: dict) -> dict:
        """Extract KPI summary from widget data for frontend format."""
        ie = data.get(WidgetType.INCOME_EXPENSE, {})
        income = ie.get("income", {}) if isinstance(ie, dict) else {}
        expense = ie.get("expense", {}) if isinstance(ie, dict) else {}
        acct = data.get(WidgetType.ACCOUNT_SUMMARY, {})
        acct_count = acct.get("account_count", 0) if isinstance(acct, dict) else 0
        net_worth = acct.get("total_balance", 0.0) if isinstance(acct, dict) else 0.0
        return {
            "total_income": income.get("total", 0.0) if isinstance(income, dict) else 0.0,
            "total_expenses": expense.get("total", 0.0) if isinstance(expense, dict) else 0.0,
            "total_net_worth": net_worth,
            "account_count": acct_count,
            "transaction_count": (income.get("count", 0) if isinstance(income, dict) else 0) +
                                  (expense.get("count", 0) if isinstance(expense, dict) else 0),
        }

    def _extract_recent_transactions(self, data: dict) -> list:
        """Extract recent transactions list from widget data."""
        widget_data = data.get(WidgetType.RECENT_TRANSACTIONS, [])
        if isinstance(widget_data, list):
            return widget_data
        if isinstance(widget_data, dict):
            return widget_data.get("items", [])
        return []

    def _extract_upcoming_payments(self, data: dict) -> list:
        """Extract upcoming payments list from widget data."""
        widget_data = data.get(WidgetType.PLANNED_PAYMENTS, {})
        if isinstance(widget_data, list):
            return widget_data
        if isinstance(widget_data, dict):
            return widget_data.get("items", [])
        return []

    async def update_widget(
        self, widget_id: uuid.UUID, user_id: uuid.UUID,
        tenant_id: uuid.UUID, data: dict
    ):
        widget = await self.repo.get_by_id(widget_id, user_id)
        if not widget:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Widget not found.")
        updated = await self.repo.update(widget, data)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def list_widgets(self, user_id: uuid.UUID, tenant_id: uuid.UUID):
        return await self.repo.get_user_widgets(user_id, tenant_id)

    async def _get_recent_transactions(self, tenant_id: uuid.UUID, group_ids: Optional[List[uuid.UUID]] = None, limit: int = 10) -> list:
        """Fetch the most recent confirmed transactions for the dashboard."""
        from sqlalchemy import select, or_
        from app.models.transaction import Transaction, TransactionStatus
        q = (
            select(Transaction)
            .where(
                Transaction.tenant_id == tenant_id,
                Transaction.status == TransactionStatus.CONFIRMED,
                Transaction.is_deleted == False,
            )
        )
        if group_ids:
            q = q.where(Transaction.group_id.in_(group_ids))
        q = (
            q
            .order_by(Transaction.transaction_date.desc())
            .limit(limit)
        )
        rows = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "id": str(t.id),
                "transaction_type": t.transaction_type,
                "amount": float(t.amount),
                "currency": t.currency,
                "description": t.description,
                "transaction_date": str(t.transaction_date),
                "status": t.status,
            }
            for t in rows
        ]

    async def _get_account_summary(self, tenant_id: uuid.UUID, group_ids: Optional[List[uuid.UUID]] = None) -> dict:
        """Fetch a basic summary of all active accounts."""
        from sqlalchemy import select, or_
        from app.models.account import Account
        from decimal import Decimal

        q = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_active == True,
            Account.is_deleted == False,
        )
        if group_ids:
            q = q.where(Account.group_id.in_(group_ids))
        accounts = list((await self.db.execute(q)).scalars().all())
        total = sum((a.current_balance or Decimal("0")) for a in accounts)
        return {
            "account_count": len(accounts),
            "total_balance": float(total),
            "accounts": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "balance": float(a.current_balance or 0),
                    "currency": a.currency,
                }
                for a in accounts[:5]
            ],
        }
