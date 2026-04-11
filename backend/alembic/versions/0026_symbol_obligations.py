"""Add symbol_obligations table

Revision ID: 0026_symbol_obligations
Revises: 0025_permissions_delete_requests
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0026_symbol_obligations'
down_revision = '0025_permissions_delete_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'symbol_obligations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 6), nullable=False),
        sa.Column('price_per_unit', sa.Numeric(20, 6), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='TRY'),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('counterparty_type', sa.String(10), nullable=False),
        sa.Column('counterparty_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('counterparty_name', sa.String(255), nullable=True),
        sa.Column('due_date', sa.Date, nullable=True),
        sa.Column('status', sa.String(15), nullable=False, server_default='PENDING'),
        sa.Column('peer_obligation_id', UUID(as_uuid=True), sa.ForeignKey('symbol_obligations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_sym_oblig_user', 'symbol_obligations', ['user_id'])
    op.create_index('ix_sym_oblig_tenant', 'symbol_obligations', ['tenant_id'])
    op.create_index('ix_sym_oblig_counterparty_user', 'symbol_obligations', ['counterparty_user_id'])


def downgrade() -> None:
    op.drop_table('symbol_obligations')
