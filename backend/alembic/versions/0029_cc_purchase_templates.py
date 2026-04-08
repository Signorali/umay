"""Credit card purchase templates.

Revision ID: 0029_cc_purchase_templates
Revises: 0028_transaction_templates
Create Date: 2026-04-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0029_cc_purchase_templates'
down_revision = '0028_transaction_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cc_purchase_templates',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('installment_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='TRY'),
        sa.Column('category_id', sa.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_deleted', sa.Boolean, server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_table('cc_purchase_templates')
