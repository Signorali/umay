"""Link investment accounts to institutions and portfolios to cash accounts.

Revision ID: 0018_investment_account_link
Revises: 0017_normalize_symbols
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0018_investment_account_link"
down_revision: Union[str, None] = "0017_normalize_symbols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add institution_id FK to accounts (nullable — existing accounts unaffected)
    op.add_column(
        "accounts",
        sa.Column("institution_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_accounts_institution_id",
        "accounts", "institutions",
        ["institution_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_accounts_institution_id", "accounts", ["institution_id"])

    # Add cash_account_id FK to portfolios (nullable — existing portfolios unaffected)
    op.add_column(
        "portfolios",
        sa.Column("cash_account_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_portfolios_cash_account_id",
        "portfolios", "accounts",
        ["cash_account_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_portfolios_cash_account_id", "portfolios", ["cash_account_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolios_cash_account_id", table_name="portfolios")
    op.drop_constraint("fk_portfolios_cash_account_id", "portfolios", type_="foreignkey")
    op.drop_column("portfolios", "cash_account_id")

    op.drop_index("ix_accounts_institution_id", table_name="accounts")
    op.drop_constraint("fk_accounts_institution_id", "accounts", type_="foreignkey")
    op.drop_column("accounts", "institution_id")
