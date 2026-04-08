"""Add production performance indexes for millions of records.

Revision ID: 0027_performance_indexes
Revises: 0026_symbol_obligations
Create Date: 2026-04-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0027_performance_indexes'
down_revision = '0026_symbol_obligations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for high-volume operations."""

    # === TRANSACTIONS ===
    # Fast lookup by tenant + date range
    op.create_index(
        'ix_transactions_tenant_date_idx',
        'transactions',
        ['tenant_id', 'transaction_date'],
        if_not_exists=True
    )
    # Category breakdown queries
    op.create_index(
        'ix_transactions_category_period_idx',
        'transactions',
        ['category_id', 'transaction_date'],
        if_not_exists=True
    )

    # === INVESTMENTS ===
    # Portfolio position lookups
    op.create_index(
        'ix_portfolio_positions_portfolio_symbol_idx',
        'portfolio_positions',
        ['portfolio_id', 'symbol'],
        if_not_exists=True
    )
    # Investment transaction history
    op.create_index(
        'ix_investment_tx_portfolio_date_idx',
        'investment_transactions',
        ['portfolio_id', 'transaction_date'],
        if_not_exists=True
    )
    # Symbol queries
    op.create_index(
        'ix_investment_tx_symbol_idx',
        'investment_transactions',
        ['symbol'],
        if_not_exists=True
    )

    # === WATCHLIST ===
    # User's pinned symbols (market ticker)
    op.create_index(
        'ix_watchlist_user_pinned_idx',
        'watchlist_items',
        ['user_id', 'is_pinned', 'display_order'],
        if_not_exists=True
    )
    # Price snapshots for fast updates
    op.create_index(
        'ix_price_snapshot_symbol_date_idx',
        'price_snapshots',
        ['symbol', 'snapshot_at'],
        if_not_exists=True
    )

    # === CALENDAR ===
    # Upcoming calendar items
    op.create_index(
        'ix_calendar_items_user_date_idx',
        'calendar_items',
        ['user_id', 'due_date'],
        if_not_exists=True
    )
    # Calendar syncs
    op.create_index(
        'ix_calendar_integration_user_provider_idx',
        'calendar_integrations',
        ['user_id', 'provider'],
        if_not_exists=True
    )

    # === OBLIGATIONS ===
    # User's active obligations
    op.create_index(
        'ix_symbol_obligations_user_status_idx',
        'symbol_obligations',
        ['user_id', 'status', 'due_date'],
        if_not_exists=True
    )

    # === ACCOUNTS ===
    # Dashboard account listing
    op.create_index(
        'ix_accounts_tenant_active_idx',
        'accounts',
        ['tenant_id', 'is_deleted'],
        if_not_exists=True
    )

    # === CREDIT & LOANS ===
    # Loan statement queries
    op.create_index(
        'ix_loan_installments_loan_status_idx',
        'loan_installments',
        ['loan_id', 'status'],
        if_not_exists=True
    )
    # Credit card statements
    op.create_index(
        'ix_credit_card_statements_card_date_idx',
        'credit_card_statements',
        ['card_id', 'period_start'],
        if_not_exists=True
    )

    # === CATEGORIES ===
    # Fast category tree traversal
    op.create_index(
        'ix_categories_parent_idx',
        'categories',
        ['parent_id'],
        if_not_exists=True
    )

    # === COMMON QUERIES ===
    # Tenant-wide queries (multi-tenant safety)
    op.create_index(
        'ix_accounts_tenant_idx',
        'accounts',
        ['tenant_id'],
        if_not_exists=True
    )
    op.create_index(
        'ix_transactions_tenant_idx',
        'transactions',
        ['tenant_id'],
        if_not_exists=True
    )
    op.create_index(
        'ix_portfolios_tenant_idx',
        'portfolios',
        ['tenant_id'],
        if_not_exists=True
    )


def downgrade() -> None:
    """Remove performance indexes."""

    indexes_to_drop = [
        'ix_transactions_tenant_date_idx',
        'ix_transactions_category_period_idx',
        'ix_portfolio_positions_portfolio_symbol_idx',
        'ix_investment_tx_portfolio_date_idx',
        'ix_investment_tx_symbol_idx',
        'ix_watchlist_user_pinned_idx',
        'ix_price_snapshot_symbol_date_idx',
        'ix_calendar_items_user_date_idx',
        'ix_calendar_integration_user_provider_idx',
        'ix_symbol_obligations_user_status_idx',
        'ix_accounts_tenant_active_idx',
        'ix_loan_installments_loan_status_idx',
        'ix_credit_card_statements_card_date_idx',
        'ix_categories_parent_idx',
        'ix_accounts_tenant_idx',
        'ix_transactions_tenant_idx',
        'ix_portfolios_tenant_idx',
    ]

    for idx in indexes_to_drop:
        op.drop_index(idx, if_exists=True)
