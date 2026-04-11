"""Add formula column to watchlist_items

Revision ID: 0022_watchlist_formula
Revises: 0021_commission_tx_id
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0022_watchlist_formula'
down_revision = '0021_commission_tx_id'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'watchlist_items',
        sa.Column('formula', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('watchlist_items', 'formula')
