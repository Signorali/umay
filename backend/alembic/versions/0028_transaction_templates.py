"""Transaction templates — saved transaction presets.

Revision ID: 0028_transaction_templates
Revises: 0027_performance_indexes
Create Date: 2026-04-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0028_transaction_templates'
down_revision = '0027_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'transaction_templates',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('transaction_type', sa.String(20), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='TRY'),
        sa.Column('source_account_id', sa.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_account_id', sa.UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('category_id', sa.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_table('transaction_templates')
