"""Add change_percent and trend to price_snapshots

Revision ID: 0009_market_price_change
Revises: 0009_ocr_drafts
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0009_market_price_change"
down_revision: Union[str, None] = "0009_ocr_drafts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_snapshots",
        sa.Column("change_percent", sa.Numeric(precision=10, scale=4), nullable=True)
    )
    op.add_column(
        "price_snapshots",
        sa.Column("trend", sa.String(20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("price_snapshots", "trend")
    op.drop_column("price_snapshots", "change_percent")
