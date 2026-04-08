"""Add source column to watchlist_items

Revision ID: 0010_watchlist_source
Revises: 0010_calendar_sync
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010_watchlist_source"
down_revision: Union[str, None] = "0010_calendar_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "watchlist_items",
        sa.Column("source", sa.String(50), nullable=False, server_default="google_finance")
    )


def downgrade() -> None:
    op.drop_column("watchlist_items", "source")
