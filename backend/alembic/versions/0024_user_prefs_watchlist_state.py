"""user ui_theme + watchlist is_pinned/display_order — move state from localStorage to DB

Revision ID: 0024
Revises: 0023
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0024_user_prefs_watchlist_state'
down_revision = '0023_calendar_integrations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # User UI theme preference
    op.add_column('users', sa.Column('ui_theme', sa.String(20), nullable=True))

    # Watchlist pin + display order (replaces localStorage)
    op.add_column('watchlist_items', sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('watchlist_items', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('watchlist_items', 'display_order')
    op.drop_column('watchlist_items', 'is_pinned')
    op.drop_column('users', 'ui_theme')
