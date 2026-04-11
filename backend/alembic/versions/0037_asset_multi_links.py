"""asset_loan_links and asset_account_links: many-to-many loans and accounts per asset

Revision ID: 0037_asset_multi_links
Revises: 0036_watchlist_user_pins
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0037_asset_multi_links'
down_revision = '0036_watchlist_user_pins'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset_loan_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('loan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'loan_id', name='uq_asset_loan_link'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_asset_loan_links_asset_id', 'asset_loan_links', ['asset_id'])

    op.create_table(
        'asset_account_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('link_type', sa.String(20), nullable=False, server_default='source'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'account_id', name='uq_asset_account_link'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_asset_account_links_asset_id', 'asset_account_links', ['asset_id'])

    # Migrate existing single-FK data into junction tables
    op.execute("""
        INSERT INTO asset_loan_links (asset_id, loan_id)
        SELECT id, loan_id FROM assets
        WHERE loan_id IS NOT NULL AND is_deleted = false
        ON CONFLICT (asset_id, loan_id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO asset_account_links (asset_id, account_id, link_type)
        SELECT id, source_account_id, 'source' FROM assets
        WHERE source_account_id IS NOT NULL AND is_deleted = false
        ON CONFLICT (asset_id, account_id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO asset_account_links (asset_id, account_id, link_type)
        SELECT id, account_id, 'linked' FROM assets
        WHERE account_id IS NOT NULL AND is_deleted = false
        ON CONFLICT (asset_id, account_id) DO NOTHING
    """)


def downgrade():
    op.drop_index('ix_asset_account_links_asset_id', table_name='asset_account_links')
    op.drop_table('asset_account_links')
    op.drop_index('ix_asset_loan_links_asset_id', table_name='asset_loan_links')
    op.drop_table('asset_loan_links')
