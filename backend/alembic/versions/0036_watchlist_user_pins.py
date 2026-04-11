"""watchlist_user_pins table for per-user pin/display_order preferences

Revision ID: 0036_watchlist_user_pins
Revises: 0035_loan_category_id
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0036_watchlist_user_pins'
down_revision = '0035_loan_category_id'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'watchlist_user_pins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='9999'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'item_id', name='uq_watchlist_user_pin'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['watchlist_items.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_watchlist_user_pins_user_id', 'watchlist_user_pins', ['user_id'])


def downgrade():
    op.drop_index('ix_watchlist_user_pins_user_id', table_name='watchlist_user_pins')
    op.drop_table('watchlist_user_pins')
