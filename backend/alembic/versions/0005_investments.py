"""Phase 3 — Investments (portfolios, transactions, positions)

Revision ID: 0005_investments
Revises: 0004_institutions
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_investments"
down_revision: Union[str, None] = "0004_institutions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolios",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("institution_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_portfolios_tenant_id", "portfolios", ["tenant_id"])

    op.create_table(
        "investment_transactions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("portfolio_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.Text(), nullable=False),
        sa.Column("instrument_type", sa.Text(), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("commission", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("fx_rate", sa.Numeric(precision=20, scale=8), nullable=True, server_default="1"),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("linked_transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_inv_tx_portfolio", "investment_transactions", ["portfolio_id"])
    op.create_index("ix_inv_tx_date", "investment_transactions", ["portfolio_id", "transaction_date"])
    op.create_index("ix_inv_tx_symbol", "investment_transactions", ["symbol"])

    op.create_table(
        "portfolio_positions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("portfolio_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("instrument_type", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False, server_default="0"),
        sa.Column("avg_cost", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("total_cost", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("current_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("current_value", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
    )
    op.create_index("ix_positions_portfolio", "portfolio_positions", ["portfolio_id"])


def downgrade() -> None:
    op.drop_index("ix_positions_portfolio", table_name="portfolio_positions")
    op.drop_table("portfolio_positions")
    op.drop_index("ix_inv_tx_symbol", table_name="investment_transactions")
    op.drop_index("ix_inv_tx_date", table_name="investment_transactions")
    op.drop_index("ix_inv_tx_portfolio", table_name="investment_transactions")
    op.drop_table("investment_transactions")
    op.drop_index("ix_portfolios_tenant_id", table_name="portfolios")
    op.drop_table("portfolios")
