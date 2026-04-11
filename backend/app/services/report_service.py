"""ReportService — income/expense, account movement, cash flow, category, asset, and investment reports.

cloud.md §8.12: income/expense, account movement, category, group, loan, credit card,
               asset, investment performance, cash flow projection.
"""
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionStatus
from app.models.ledger import LedgerEntry
from app.models.account import Account
from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus
from app.models.loan import Loan, LoanInstallment, InstallmentStatus, LoanStatus
from app.models.credit_card import CreditCard, CreditCardStatement, StatementStatus
from app.models.asset import Asset
from app.models.investment import Portfolio, InvestmentTransaction, InvestmentTransactionType
from app.models.category import Category


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── §8.12 Income/Expense ─────────────────────────────────────────────────

    async def income_expense_report(
        self,
        tenant_id: uuid.UUID,
        period_start: date,
        period_end: date,
        group_id: Optional[uuid.UUID] = None,
        group_ids: Optional[List[uuid.UUID]] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> dict:
        from sqlalchemy import or_
        q = select(
            Transaction.transaction_type,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).where(
            Transaction.tenant_id == tenant_id,
            Transaction.status == TransactionStatus.CONFIRMED,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
            Transaction.is_deleted == False,
        )
        if group_ids:
            q = q.where(Transaction.group_id.in_(group_ids))
        elif group_id:
            q = q.where(Transaction.group_id == group_id)
        if category_id:
            q = q.where(Transaction.category_id == category_id)
        q = q.group_by(Transaction.transaction_type)

        rows = (await self.db.execute(q)).all()
        result = {
            "income": {"total": 0.0, "count": 0},
            "expense": {"total": 0.0, "count": 0},
            "transfer": {"total": 0.0, "count": 0},
        }
        for row in rows:
            key = row.transaction_type.lower()
            if key in result:
                result[key] = {"total": float(row.total or 0), "count": row.count}

        result["net"] = result["income"]["total"] - result["expense"]["total"]
        result["period"] = {"start": str(period_start), "end": str(period_end)}
        return result

    # ── §8.12 Account Movement ───────────────────────────────────────────────

    async def account_movement_report(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> dict:
        acct_q = select(Account).where(
            Account.id == account_id,
            Account.tenant_id == tenant_id,
            Account.is_deleted == False,
        )
        account = (await self.db.execute(acct_q)).scalar_one_or_none()
        if not account:
            return {"error": "Account not found"}

        entries_q = select(
            LedgerEntry.entry_type,
            func.sum(LedgerEntry.amount).label("total"),
            func.count(LedgerEntry.id).label("count"),
        ).where(
            LedgerEntry.account_id == account_id,
            func.date(LedgerEntry.posted_at) >= period_start,
            func.date(LedgerEntry.posted_at) <= period_end,
            LedgerEntry.is_deleted == False,
        ).group_by(LedgerEntry.entry_type)

        rows = (await self.db.execute(entries_q)).all()
        debits = next((r for r in rows if r.entry_type == "DEBIT"), None)
        credits = next((r for r in rows if r.entry_type == "CREDIT"), None)

        return {
            "account_id": str(account_id),
            "account_name": account.name,
            "currency": account.currency,
            "current_balance": float(account.current_balance),
            "period": {"start": str(period_start), "end": str(period_end)},
            "debits": {"total": float(debits.total or 0), "count": debits.count if debits else 0},
            "credits": {"total": float(credits.total or 0), "count": credits.count if credits else 0},
            "net": float((credits.total or 0) - (debits.total or 0)) if credits or debits else 0.0,
        }

    # ── §8.12 Category Breakdown ─────────────────────────────────────────────

    async def category_breakdown(
        self,
        tenant_id: uuid.UUID,
        period_start: date,
        period_end: date,
        transaction_type: str = "EXPENSE",
        group_id: Optional[uuid.UUID] = None,
    ) -> list:
        q = select(
            Transaction.category_id,
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        ).outerjoin(
            Category, Transaction.category_id == Category.id,
        ).where(
            Transaction.tenant_id == tenant_id,
            Transaction.status == TransactionStatus.CONFIRMED,
            Transaction.transaction_type == transaction_type,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
            Transaction.is_deleted == False,
        )
        if group_id:
            q = q.where(Transaction.group_id == group_id)
        q = q.group_by(Transaction.category_id, Category.name).order_by(func.sum(Transaction.amount).desc())

        rows = (await self.db.execute(q)).all()
        return [
            {
                "category_id": str(row.category_id) if row.category_id else None,
                "category_name": row.category_name or "Kategorisiz",
                "total": float(row.total or 0),
                "count": row.count,
            }
            for row in rows
        ]

    # ── §8.12 Cash Flow Projection ───────────────────────────────────────────

    async def cash_flow_projection(
        self,
        tenant_id: uuid.UUID,
        months_ahead: int = 0,
        group_id: Optional[uuid.UUID] = None,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> list:
        """Project cash flow from pending planned payments.

        months_ahead=0 → return ALL pending payments (no date limit).
        months_ahead>0 → return payments within the given month window.
        """
        from sqlalchemy import or_

        q = select(PlannedPayment).where(
            PlannedPayment.tenant_id == tenant_id,
            PlannedPayment.status == PlannedPaymentStatus.PENDING,
            PlannedPayment.is_deleted == False,
        )

        if months_ahead > 0:
            today = date.today()
            end_date = today + timedelta(days=months_ahead * 30)
            q = q.where(PlannedPayment.planned_date <= end_date)

        if group_ids:
            q = q.where(PlannedPayment.group_id.in_(group_ids))
        elif group_id:
            q = q.where(PlannedPayment.group_id == group_id)
        q = q.order_by(PlannedPayment.planned_date)

        payments = list((await self.db.execute(q)).scalars().all())
        return [
            {
                "date": str(p.planned_date),
                "type": p.payment_type,
                "title": p.title,
                "amount": float(p.amount - p.paid_amount),
                "currency": p.currency,
                "status": p.status,
            }
            for p in payments
        ]

    # ── §8.7 Loan Report ─────────────────────────────────────────────────────

    async def loan_report(self, tenant_id: uuid.UUID, group_id: Optional[uuid.UUID] = None, group_ids: Optional[List[uuid.UUID]] = None) -> dict:
        from sqlalchemy import or_
        q = select(Loan).where(
            Loan.tenant_id == tenant_id,
            Loan.status == LoanStatus.ACTIVE,
            Loan.is_deleted == False,
        )
        if group_ids:
            q = q.where(Loan.group_id.in_(group_ids))
        elif group_id:
            q = q.where(Loan.group_id == group_id)
        loans = list((await self.db.execute(q)).scalars().all())

        total_principal: dict = {}
        total_remaining: dict = {}
        overdue_count = 0

        for loan in loans:
            c = loan.currency
            total_principal[c] = total_principal.get(c, Decimal("0")) + loan.principal
            total_remaining[c] = total_remaining.get(c, Decimal("0")) + loan.remaining_balance

            overdue_q = select(func.count(LoanInstallment.id)).where(
                LoanInstallment.loan_id == loan.id,
                LoanInstallment.status == InstallmentStatus.OVERDUE,
                LoanInstallment.is_deleted == False,
            )
            cnt = (await self.db.execute(overdue_q)).scalar_one()
            if cnt:
                overdue_count += cnt

        return {
            "active_loan_count": len(loans),
            "total_principal": {k: float(v) for k, v in total_principal.items()},
            "total_remaining": {k: float(v) for k, v in total_remaining.items()},
            "overdue_installments": overdue_count,
        }

    # ── §8.8 Credit Card Report ──────────────────────────────────────────────

    async def credit_card_report(self, tenant_id: uuid.UUID, group_id: Optional[uuid.UUID] = None, group_ids: Optional[List[uuid.UUID]] = None) -> dict:
        from sqlalchemy import or_
        q = select(CreditCard).where(
            CreditCard.tenant_id == tenant_id,
            CreditCard.is_deleted == False,
        )
        if group_ids:
            q = q.where(CreditCard.group_id.in_(group_ids))
        elif group_id:
            q = q.where(CreditCard.group_id == group_id)
        cards = list((await self.db.execute(q)).scalars().all())

        total_limit: dict = {}
        total_debt: dict = {}
        overdue_statements = 0

        for card in cards:
            c = card.currency
            total_limit[c] = total_limit.get(c, Decimal("0")) + card.credit_limit
            total_debt[c] = total_debt.get(c, Decimal("0")) + card.current_debt

            stmt_q = select(func.count(CreditCardStatement.id)).where(
                CreditCardStatement.card_id == card.id,
                CreditCardStatement.status == StatementStatus.OVERDUE,
                CreditCardStatement.is_deleted == False,
            )
            cnt = (await self.db.execute(stmt_q)).scalar_one()
            if cnt:
                overdue_statements += cnt

        return {
            "card_count": len(cards),
            "total_limit": {k: float(v) for k, v in total_limit.items()},
            "total_debt": {k: float(v) for k, v in total_debt.items()},
            "utilization": {
                k: round(float(total_debt.get(k, 0)) / float(v) * 100, 2)
                for k, v in total_limit.items() if v
            },
            "overdue_statements": overdue_statements,
        }

    # ── §8.9 Asset Report (cloud.md) ─────────────────────────────────────────

    async def asset_report(self, tenant_id: uuid.UUID, group_id: Optional[uuid.UUID] = None) -> dict:
        """
        Aggregate all assets: total purchase value, current value,
        unrealized gain/loss (active), realized gain/loss (sold).
        Values are converted to base currency using the stored fx_rate.
        """
        from app.models.tenant import Tenant
        tenant_obj = (await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        base_currency = tenant_obj.base_currency if tenant_obj else "TRY"

        q = select(Asset).where(
            Asset.tenant_id == tenant_id,
            Asset.is_deleted == False,
        )
        if group_id:
            q = q.where(Asset.group_id == group_id)
        assets = list((await self.db.execute(q)).scalars().all())

        by_type: dict = {}
        total_purchase = Decimal("0")
        total_current = Decimal("0")
        sold_count = 0
        total_gain = Decimal("0")

        for a in assets:
            atype = str(a.asset_type)
            if atype not in by_type:
                by_type[atype] = {
                    "count": 0,
                    "total_purchase_value": Decimal("0"),
                    "total_current_value": Decimal("0"),
                }
            by_type[atype]["count"] += 1
            # Convert to base currency using stored fx_rate (default=1 for base currency assets)
            fx = Decimal(str(a.fx_rate)) if a.fx_rate else Decimal("1")
            if fx == Decimal("0"):
                fx = Decimal("1")
            pv = (a.purchase_value or Decimal("0")) * fx
            cv = (a.current_value or a.purchase_value or Decimal("0")) * fx
            by_type[atype]["total_purchase_value"] += pv
            by_type[atype]["total_current_value"] += cv
            total_purchase += pv
            total_current += cv

            if a.sale_date is not None:
                sold_count += 1
                sp = (a.sale_value or Decimal("0")) * fx
                total_gain += sp - pv

        return {
            "currency": base_currency,
            "asset_count": len(assets),
            "sold_count": sold_count,
            "total_purchase_value": float(total_purchase),
            "total_current_value": float(total_current),
            "unrealized_gain_loss": float(total_current - total_purchase),
            "realized_gain_loss": float(total_gain),
            "by_type": {
                k: {
                    "count": v["count"],
                    "total_purchase_value": float(v["total_purchase_value"]),
                    "total_current_value": float(v["total_current_value"]),
                    "unrealized_gain_loss": float(
                        v["total_current_value"] - v["total_purchase_value"]
                    ),
                }
                for k, v in by_type.items()
            },
        }

    # ── §8.10 Investment Performance Report (cloud.md) ───────────────────────

    async def investment_performance_report(
        self,
        tenant_id: uuid.UUID,
        portfolio_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Realized P&L (BUY vs SELL), dividend/interest income per portfolio.
        Also returns open positions with cost basis.
        """
        port_q = select(Portfolio).where(
            Portfolio.tenant_id == tenant_id,
            Portfolio.is_deleted == False,
        )
        if portfolio_id:
            port_q = port_q.where(Portfolio.id == portfolio_id)
        portfolios = list((await self.db.execute(port_q)).scalars().all())

        results = []
        grand_realized = Decimal("0")
        grand_income = Decimal("0")

        for port in portfolios:
            tx_q = select(InvestmentTransaction).where(
                InvestmentTransaction.portfolio_id == port.id,
                InvestmentTransaction.is_deleted == False,
            )
            txs = list((await self.db.execute(tx_q)).scalars().all())

            total_buy = Decimal("0")
            total_sell = Decimal("0")
            dividend_income = Decimal("0")
            interest_income = Decimal("0")
            symbol_positions: dict = {}

            for tx in txs:
                qty = tx.quantity or Decimal("0")
                price = tx.price or Decimal("0")
                fee = tx.commission or Decimal("0")
                net = tx.net_amount or (qty * price - fee)

                if tx.transaction_type == InvestmentTransactionType.BUY:
                    total_buy += net
                    sym = tx.symbol or "UNKNOWN"
                    if sym not in symbol_positions:
                        symbol_positions[sym] = {"qty": Decimal("0"), "cost": Decimal("0")}
                    symbol_positions[sym]["qty"] += qty
                    symbol_positions[sym]["cost"] += net

                elif tx.transaction_type == InvestmentTransactionType.SELL:
                    total_sell += net
                    sym = tx.symbol or "UNKNOWN"
                    if sym not in symbol_positions:
                        symbol_positions[sym] = {"qty": Decimal("0"), "cost": Decimal("0")}
                    symbol_positions[sym]["qty"] -= qty

                elif tx.transaction_type == InvestmentTransactionType.DIVIDEND:
                    dividend_income += net
                elif tx.transaction_type == InvestmentTransactionType.INTEREST_INCOME:
                    interest_income += net

            realized_pl = total_sell - total_buy
            grand_realized += realized_pl
            grand_income += dividend_income + interest_income

            results.append({
                "portfolio_id": str(port.id),
                "portfolio_name": port.name,
                "currency": port.currency,
                "total_invested": float(total_buy),
                "total_sold": float(total_sell),
                "realized_pl": float(realized_pl),
                "dividend_income": float(dividend_income),
                "interest_income": float(interest_income),
                "total_return": float(realized_pl + dividend_income + interest_income),
                "open_positions": {
                    sym: {
                        "quantity": float(v["qty"]),
                        "cost_basis": float(v["cost"]),
                    }
                    for sym, v in symbol_positions.items()
                    if v["qty"] > 0
                },
            })

        return {
            "portfolio_count": len(portfolios),
            "grand_realized_pl": float(grand_realized),
            "grand_income": float(grand_income),
            "portfolios": results,
        }

    # ── §20 Worker-dispatched async generation ───────────────────────────────

    async def generate_async(
        self,
        report_type: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        params: dict,
    ) -> dict:
        """
        Worker-triggered report generation (cloud.md §8.12, §20).
        Types: income_expense | category_breakdown | cash_flow |
               loans | credit_cards | assets | investment_performance
        """
        from datetime import date as date_type, datetime
        today = date_type.today()

        def _parse_date(v) -> Optional[date]:
            if isinstance(v, date):
                return v
            if isinstance(v, str):
                return datetime.strptime(v, "%Y-%m-%d").date()
            return None

        period_start = _parse_date(params.get("period_start")) or date_type(today.year, today.month, 1)
        period_end = _parse_date(params.get("period_end")) or today

        dispatch = {
            "income_expense": lambda: self.income_expense_report(
                tenant_id=tenant_id, period_start=period_start, period_end=period_end,
                group_id=params.get("group_id"), category_id=params.get("category_id"),
            ),
            "category_breakdown": lambda: self.category_breakdown(
                tenant_id=tenant_id, period_start=period_start, period_end=period_end,
                transaction_type=params.get("transaction_type", "EXPENSE"),
                group_id=params.get("group_id"),
            ),
            "cash_flow": lambda: self.cash_flow_projection(
                tenant_id=tenant_id, months_ahead=int(params.get("months_ahead", 3)),
                group_id=params.get("group_id"),
            ),
            "loans": lambda: self.loan_report(tenant_id=tenant_id),
            "credit_cards": lambda: self.credit_card_report(tenant_id=tenant_id),
            "assets": lambda: self.asset_report(tenant_id=tenant_id),
            "investment_performance": lambda: self.investment_performance_report(
                tenant_id=tenant_id, portfolio_id=params.get("portfolio_id"),
            ),
        }

        fn = dispatch.get(report_type)
        result = await fn() if fn else {"error": f"Unknown report type: {report_type}"}

        return {
            "report_type": report_type,
            "tenant_id": str(tenant_id),
            "generated_by": str(user_id),
            "params": {k: str(v) for k, v in params.items()},
            "result": result,
        }
