"""Add commission_transaction_id to investment_transactions.

Revision ID: 0021_commission_tx_id
Revises: 0020_market_prices
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0021_commission_tx_id"
down_revision: Union[str, None] = "0020_market_prices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "investment_transactions",
        sa.Column("commission_transaction_id", sa.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investment_transactions", "commission_transaction_id")
