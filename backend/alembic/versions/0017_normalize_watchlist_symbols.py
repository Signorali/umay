"""Normalize watchlist_items symbols - remove spaces around colons

Revision ID: 0017_normalize_symbols
Revises: 0016
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0017_normalize_symbols"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update symbols to remove spaces (e.g., "IST: GARAN" → "IST:GARAN")
    op.execute(
        """
        UPDATE watchlist_items
        SET symbol = REPLACE(REPLACE(symbol, ' ', ''), '  ', '')
        WHERE symbol LIKE '% %' OR symbol LIKE '%  %'
        """
    )


def downgrade() -> None:
    # No downgrade - normalization is one-way
    pass
