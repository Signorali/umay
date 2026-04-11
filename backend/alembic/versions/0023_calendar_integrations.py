"""Add calendar_integrations table

Revision ID: 0023_calendar_integrations
Revises: 0022_watchlist_formula
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = '0023_calendar_integrations'
down_revision = '0022_watchlist_formula'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'calendar_integrations',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),          # 'google' | 'microsoft'
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('calendar_id', sa.String(500), nullable=True),       # external calendar id
        sa.Column('email', sa.String(300), nullable=True),             # connected account email
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_cal_integration_user_provider'),
    )
    op.create_index('ix_cal_integrations_user', 'calendar_integrations', ['user_id'])
    op.create_index('ix_cal_integrations_tenant', 'calendar_integrations', ['tenant_id'])


def downgrade():
    op.drop_table('calendar_integrations')
