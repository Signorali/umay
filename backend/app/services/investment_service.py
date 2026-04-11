"""InvestmentService — portfolio and trades with FIFO PnL calculation.

Cash-flow rules when portfolio has a linked cash_account:
  BUY  → EXPENSE  gross_amount   from cash account  (stock purchase)
       → EXPENSE  commission     from cash account  (commission as separate cost)
  SELL → INCOME   gross_amount   to   cash account  (sale proceeds)
       → EXPENSE  commission     from cash account  (commission as separate cost)

Commission is ALWAYS recorded as a separate EXPENSE regardless of buy/sell.
Delete/update reverses the original cash flows via counter-transactions.
"""
import uuid
import logging
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.investment import (
    PortfolioRepository, InvestmentTransactionRepository, PortfolioPositionRepository,
    MarketPriceRepository
)
from app.services.audit_service import AuditService
from app.services.market_service import MarketService
from app.models.investment import InvestmentTransactionType, MarketPrice

logger = logging.getLogger(__name__)


class InvestmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.portfolio_repo = PortfolioRepository(db)
        self.tx_repo = InvestmentTransactionRepository(db)
        self.position_repo = PortfolioPositionRepository(db)
        self.market_repo = MarketPriceRepository(db)
        self.market_svc = MarketService(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ #
    # Portfolios
    # ------------------------------------------------------------------ #

    async def list_portfolios(
        self, tenant_id: uuid.UUID,
        group_id: Optional[uuid.UUID] = None,
        active_only: bool = True,
        skip: int = 0, limit: int = 50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ):
        portfolios = await self.portfolio_repo.list_by_tenant(
            tenant_id, group_id=group_id, active_only=active_only,
            skip=skip, limit=limit, group_ids=group_ids or [],
        )
        # Enrich each portfolio with aggregated position values
        for p in portfolios:
            positions = await self.position_repo.list_by_portfolio(p.id)
            p.total_value = sum(
                (pos.current_value or Decimal("0")) for pos in positions
            )
            p.unrealized_pnl = sum(
                (pos.unrealized_pnl or Decimal("0")) for pos in positions
            )
        return portfolios

    async def get_portfolio(self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID):
        return await self._get_portfolio_or_404(portfolio_id, tenant_id)

    async def create_portfolio(
        self, tenant_id: uuid.UUID, actor_id: uuid.UUID, data: dict
    ):
        p = await self.portfolio_repo.create(tenant_id, data)
        await self.db.commit()
        await self.db.refresh(p)
        return p

    async def update_portfolio(
        self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        p = await self._get_portfolio_or_404(portfolio_id, tenant_id)
        updated = await self.portfolio_repo.update(p, data)
        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    # ------------------------------------------------------------------ #
    # Market & Prices
    # ------------------------------------------------------------------ #

    async def list_market_prices(self, tenant_id: uuid.UUID):
        return await self.market_repo.list_by_tenant(tenant_id)

    async def refresh_market_prices(self, tenant_id: uuid.UUID) -> int:
        """Re-fetch all prices and update all portfolio positions with latest values."""
        items = await self.market_repo.list_by_tenant(tenant_id)
        updated = 0
        price_map: dict = {}
        for obj in items:
            await self._fetch_and_update_price(obj)
            if obj.price and obj.price > 0:
                price_map[obj.symbol] = obj
            updated += 1

        # Update all positions with fresh prices
        if price_map:
            all_positions = await self.position_repo.list_by_tenant(tenant_id)
            for pos in all_positions:
                mp = price_map.get(pos.symbol.upper())
                if mp and mp.price and mp.price > 0:
                    qty = pos.quantity or Decimal("0")
                    current_value = qty * mp.price
                    unrealized_pnl = (current_value - pos.total_cost) if pos.total_cost else None
                    await self.position_repo.update(pos, {
                        "current_price": mp.price,
                        "current_value": current_value,
                        "unrealized_pnl": unrealized_pnl,
                        "last_updated": datetime.now(timezone.utc),
                    })

        if updated:
            await self.db.commit()
        return updated

    async def add_market_symbol(
        self, tenant_id: uuid.UUID, actor_id: uuid.UUID,
        symbol: str, name: Optional[str] = None
    ):
        """Add or get a symbol in the market price tracker, fetch its price immediately."""
        obj = await self.market_repo.get_or_create(tenant_id, symbol.upper())
        if name:
            obj.name = name
        await self.db.flush()

        # Fetch price immediately
        await self._fetch_and_update_price(obj)

        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def _fetch_and_update_price(self, market_price_obj) -> None:
        """Fetch live price from Google Finance and update the MarketPrice row."""
        from app.services.market_data_service import MarketDataService
        try:
            data = await MarketDataService.fetch_google_finance_price(market_price_obj.symbol)
            if data and data.get("price") and data["price"] > 0:
                market_price_obj.price = data["price"]
                market_price_obj.currency = data.get("currency") or market_price_obj.currency
                market_price_obj.last_updated = datetime.now(timezone.utc)
                await self.db.flush()
                logger.info(f"Fetched price for {market_price_obj.symbol}: {data['price']}")
            else:
                logger.warning(f"No price returned for {market_price_obj.symbol}")
        except Exception as e:
            logger.warning(f"Price fetch failed for {market_price_obj.symbol}: {e}")

    async def update_market_price(
        self, tenant_id: uuid.UUID, symbol: str,
        price: Decimal, name: Optional[str] = None
    ):
        obj = await self.market_repo.get_or_create(tenant_id, symbol)
        update_data: dict = {"price": price, "last_updated": datetime.now(timezone.utc)}
        if name:
            update_data["name"] = name
        for k, v in update_data.items():
            setattr(obj, k, v)
        await self.db.flush()
        return obj

    async def remove_market_symbol(self, tenant_id: uuid.UUID, symbol: str):
        await self.market_repo.delete_by_symbol(tenant_id, symbol)
        await self.db.commit()

    # ------------------------------------------------------------------ #
    # Transactions
    # ------------------------------------------------------------------ #

    async def record_transaction(
        self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        portfolio = await self._get_portfolio_or_404(portfolio_id, tenant_id)
        tx = await self.tx_repo.create(portfolio_id, data)

        tx_type = data.get("transaction_type") or tx.transaction_type
        symbol = data.get("symbol") or tx.symbol
        is_trade = str(tx_type) in ("BUY", "SELL")

        if symbol:
            mp_obj = await self.market_repo.get_or_create(tenant_id, symbol)
            if not mp_obj.price or mp_obj.price == 0:
                await self._fetch_and_update_price(mp_obj)

            if is_trade:
                await self._recalculate_position(portfolio_id, symbol)

        # ── Cash-flow entries on the linked investment account ──
        if portfolio.cash_account_id and is_trade:
            is_buy = str(tx_type) == "BUY"
            gross = tx.gross_amount or Decimal("0")
            commission = tx.commission or Decimal("0")

            # Balance check for BUY
            if is_buy and gross > 0:
                await self._check_sufficient_balance(
                    portfolio.cash_account_id,
                    gross + commission,
                    tx.currency,
                )
                main_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "EXPENSE",
                    gross, tx.currency, tx.transaction_date,
                    f"Hisse Alış: {symbol}",
                )
                tx.linked_transaction_id = main_tx.id

            elif not is_buy and gross > 0:
                main_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "INCOME",
                    gross, tx.currency, tx.transaction_date,
                    f"Hisse Satış: {symbol}",
                )
                tx.linked_transaction_id = main_tx.id

            # Commission always a separate EXPENSE
            if commission > 0:
                comm_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "EXPENSE",
                    commission, tx.currency, tx.transaction_date,
                    f"Komisyon: {symbol} {'Alış' if is_buy else 'Satış'}",
                )
                tx.commission_transaction_id = comm_tx.id

            await self.db.flush()

        await self.audit.log(
            actor_id=actor_id, action="investment.transaction",
            module="investments", record_id=tx.id,
            new_state={"type": str(tx_type), "symbol": symbol, "net_amount": str(tx.net_amount)},
        )
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def delete_transaction(
        self, tx_id: uuid.UUID, portfolio_id: uuid.UUID,
        tenant_id: uuid.UUID, actor_id: uuid.UUID
    ):
        """Soft-delete an investment transaction and reverse its cash flows."""
        portfolio = await self._get_portfolio_or_404(portfolio_id, tenant_id)
        tx = await self.tx_repo.get_by_id(tx_id, portfolio_id)
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

        is_trade = str(tx.transaction_type) in ("BUY", "SELL")
        symbol = tx.symbol

        # Reverse cash flows
        if portfolio.cash_account_id and is_trade:
            if tx.linked_transaction_id:
                await self._reverse_cash_by_id(tenant_id, tx.linked_transaction_id)
            if tx.commission_transaction_id:
                await self._reverse_cash_by_id(tenant_id, tx.commission_transaction_id)

        # Soft-delete the investment transaction
        tx.is_deleted = True
        await self.db.flush()

        # Recalculate position
        if symbol and is_trade:
            await self._recalculate_position(portfolio_id, symbol)

        await self.audit.log(
            actor_id=actor_id, action="investment.transaction.delete",
            module="investments", record_id=tx_id,
        )
        await self.db.commit()

    async def update_transaction(
        self, tx_id: uuid.UUID, portfolio_id: uuid.UUID,
        tenant_id: uuid.UUID, actor_id: uuid.UUID, data: dict
    ):
        """Update an investment transaction: reverse old cash flows, apply new ones."""
        portfolio = await self._get_portfolio_or_404(portfolio_id, tenant_id)
        tx = await self.tx_repo.get_by_id(tx_id, portfolio_id)
        if not tx:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

        old_symbol = tx.symbol
        old_is_trade = str(tx.transaction_type) in ("BUY", "SELL")

        # Reverse old cash flows first (so balance is restored before new check)
        if portfolio.cash_account_id and old_is_trade:
            if tx.linked_transaction_id:
                await self._reverse_cash_by_id(tenant_id, tx.linked_transaction_id)
                tx.linked_transaction_id = None
            if tx.commission_transaction_id:
                await self._reverse_cash_by_id(tenant_id, tx.commission_transaction_id)
                tx.commission_transaction_id = None
            await self.db.flush()

        # Update transaction fields
        allowed = {
            "transaction_type", "instrument_type", "symbol", "description",
            "quantity", "price", "gross_amount", "commission", "tax", "net_amount",
            "currency", "fx_rate", "transaction_date", "settlement_date",
            "reference_number", "notes",
        }
        for k, v in data.items():
            if k in allowed and v is not None:
                setattr(tx, k, v)
        await self.db.flush()

        # Apply new cash flows
        new_type = str(tx.transaction_type)
        new_is_trade = new_type in ("BUY", "SELL")
        new_symbol = tx.symbol

        if portfolio.cash_account_id and new_is_trade:
            is_buy = new_type == "BUY"
            gross = tx.gross_amount or Decimal("0")
            commission = tx.commission or Decimal("0")

            if is_buy and gross > 0:
                await self._check_sufficient_balance(
                    portfolio.cash_account_id, gross + commission, tx.currency
                )
                main_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "EXPENSE",
                    gross, tx.currency, tx.transaction_date,
                    f"Hisse Alış: {new_symbol}",
                )
                tx.linked_transaction_id = main_tx.id

            elif not is_buy and gross > 0:
                main_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "INCOME",
                    gross, tx.currency, tx.transaction_date,
                    f"Hisse Satış: {new_symbol}",
                )
                tx.linked_transaction_id = main_tx.id

            if commission > 0:
                comm_tx = await self._post_cash(
                    tenant_id, portfolio.cash_account_id, "EXPENSE",
                    commission, tx.currency, tx.transaction_date,
                    f"Komisyon: {new_symbol} {'Alış' if is_buy else 'Satış'}",
                )
                tx.commission_transaction_id = comm_tx.id

            await self.db.flush()

        # Recalculate positions (old symbol and/or new symbol)
        symbols_to_recalc = set()
        if old_symbol and old_is_trade:
            symbols_to_recalc.add(old_symbol)
        if new_symbol and new_is_trade:
            symbols_to_recalc.add(new_symbol)
        for sym in symbols_to_recalc:
            await self._recalculate_position(portfolio_id, sym)

        await self.audit.log(
            actor_id=actor_id, action="investment.transaction.update",
            module="investments", record_id=tx_id,
            new_state={"type": new_type, "symbol": new_symbol},
        )
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def list_transactions(
        self,
        portfolio_id: uuid.UUID, tenant_id: uuid.UUID,
        symbol=None, transaction_type=None,
        date_from=None, date_to=None,
        skip=0, limit=100,
    ):
        await self._get_portfolio_or_404(portfolio_id, tenant_id)
        return await self.tx_repo.list_by_portfolio(
            portfolio_id, symbol=symbol, transaction_type=transaction_type,
            date_from=date_from, date_to=date_to, skip=skip, limit=limit,
        )

    # ------------------------------------------------------------------ #
    # Positions
    # ------------------------------------------------------------------ #

    async def get_positions(self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID):
        await self._get_portfolio_or_404(portfolio_id, tenant_id)
        return await self.position_repo.list_by_portfolio(portfolio_id)

    async def list_all_positions(self, tenant_id: uuid.UUID):
        return await self.position_repo.list_by_tenant(tenant_id)

    async def update_position_price(
        self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID,
        symbol: str, current_price: Decimal
    ):
        await self._get_portfolio_or_404(portfolio_id, tenant_id)
        pos = await self.position_repo.get_or_create(portfolio_id, symbol)
        current_value = pos.quantity * current_price if pos.quantity else Decimal("0")
        unrealized_pnl = (
            (current_value - pos.total_cost) if pos.total_cost else None
        )
        await self.position_repo.update(pos, {
            "current_price": current_price,
            "current_value": current_value,
            "unrealized_pnl": unrealized_pnl,
            "last_updated": datetime.now(timezone.utc),
        })
        await self.db.commit()
        return pos

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _check_sufficient_balance(
        self, account_id: uuid.UUID, required: Decimal, currency: str
    ):
        """Raise HTTP 400 if the account balance is insufficient."""
        from app.models.account import Account
        account = (await self.db.execute(
            select(Account).where(Account.id == account_id)
        )).scalar_one_or_none()
        if account and account.current_balance < required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Yetersiz bakiye. Hesap bakiyesi: "
                    f"{float(account.current_balance):.2f} {account.currency}, "
                    f"gereken: {float(required):.2f} {currency}"
                )
            )

    async def _post_cash(
        self,
        tenant_id: uuid.UUID,
        cash_account_id: uuid.UUID,
        direction: str,
        amount: Decimal,
        currency: str,
        tx_date: date,
        description: str,
    ):
        """Create a confirmed EXPENSE or INCOME transaction on the cash account."""
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        from app.services.ledger_service import LedgerService

        is_expense = direction == "EXPENSE"
        cash_tx = Transaction(
            tenant_id=tenant_id,
            transaction_type=TransactionType.EXPENSE if is_expense else TransactionType.INCOME,
            status=TransactionStatus.CONFIRMED,
            amount=abs(amount),
            currency=currency,
            source_account_id=cash_account_id if is_expense else None,
            target_account_id=None if is_expense else cash_account_id,
            category_id=None,
            transaction_date=tx_date,
            description=description,
        )
        self.db.add(cash_tx)
        await self.db.flush()
        await self.db.refresh(cash_tx)

        ledger = LedgerService(self.db)
        await ledger.post_transaction(cash_tx)

        logger.info(f"Cash {direction}: {amount} {currency} — {description}")
        return cash_tx

    async def _reverse_cash_by_id(self, tenant_id: uuid.UUID, cash_tx_id: uuid.UUID):
        """Soft-delete a cash transaction and restore the account balance directly."""
        from app.models.transaction import Transaction
        from app.models.account import Account

        result = await self.db.execute(
            select(Transaction).where(
                Transaction.id == cash_tx_id,
                Transaction.is_deleted == False,
            )
        )
        cash_tx = result.scalar_one_or_none()
        if not cash_tx:
            return

        is_expense = str(cash_tx.transaction_type) == "EXPENSE"
        account_id = cash_tx.source_account_id if is_expense else cash_tx.target_account_id

        # Restore balance: EXPENSE → add back, INCOME → subtract back
        if account_id:
            acc_result = await self.db.execute(
                select(Account).where(Account.id == account_id)
            )
            account = acc_result.scalar_one_or_none()
            if account:
                if is_expense:
                    account.current_balance += cash_tx.amount
                else:
                    account.current_balance -= cash_tx.amount
                await self.db.flush()

        # Also soft-delete ledger entries
        from sqlalchemy import update
        try:
            from app.models.ledger import LedgerEntry
            await self.db.execute(
                update(LedgerEntry)
                .where(LedgerEntry.transaction_id == cash_tx_id)
                .values(is_deleted=True)
            )
        except Exception:
            pass

        # Soft-delete the cash transaction itself
        cash_tx.is_deleted = True
        await self.db.flush()
        logger.info(f"Deleted cash tx {cash_tx_id}: {cash_tx.description}")

    async def _recalculate_position(self, portfolio_id: uuid.UUID, symbol: str):
        """FIFO-based position recalculation after a buy or sell."""
        history = await self.tx_repo.get_symbol_history(portfolio_id, symbol)
        pos = await self.position_repo.get_or_create(portfolio_id, symbol)

        queue: List[dict] = []
        realized_pnl = Decimal("0")

        for tx in history:
            qty = tx.quantity or Decimal("0")
            price = tx.price or Decimal("0")

            if tx.transaction_type in (InvestmentTransactionType.BUY, "BUY"):
                queue.append({"qty": qty, "cpu": price})
            elif tx.transaction_type in (InvestmentTransactionType.SELL, "SELL"):
                remaining_sell = qty
                while remaining_sell > 0 and queue:
                    lot = queue[0]
                    sold = min(lot["qty"], remaining_sell)
                    realized_pnl += sold * (price - lot["cpu"])
                    lot["qty"] -= sold
                    remaining_sell -= sold
                    if lot["qty"] == 0:
                        queue.pop(0)

        total_qty = sum(lot["qty"] for lot in queue)
        total_cost = sum(lot["qty"] * lot["cpu"] for lot in queue)
        avg_cost = (total_cost / total_qty) if total_qty > 0 else Decimal("0")

        if total_qty <= 0:
            # No remaining holdings — soft-delete the position (may have just been created)
            pos.is_deleted = True
            pos.quantity = Decimal("0")
            await self.db.flush()
        else:
            await self.position_repo.update(pos, {
                "quantity": total_qty,
                "avg_cost": avg_cost,
                "total_cost": total_cost,
                "realized_pnl": realized_pnl,
                "last_updated": datetime.now(timezone.utc),
            })

    async def _get_portfolio_or_404(self, portfolio_id: uuid.UUID, tenant_id: uuid.UUID):
        p = await self.portfolio_repo.get_by_id(portfolio_id, tenant_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found.")
        return p
