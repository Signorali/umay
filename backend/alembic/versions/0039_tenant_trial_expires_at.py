"""tenant trial_expires_at + tenant_licenses table

Revision ID: 0039
Revises: 0038_institution_group_links
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = '0039'
down_revision = '0038_institution_group_links'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tenant_licenses tablosu
    op.create_table(
        'tenant_licenses',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('license_key', sa.Text, nullable=False),
        sa.Column('license_id', sa.String(36), nullable=False, unique=True),
        sa.Column('plan', sa.String(50), nullable=False, default='trial'),
        sa.Column('issued_to', sa.String(255), nullable=False),
        sa.Column('max_users', sa.Integer, nullable=False, default=2),
        sa.Column('features_json', sa.Text, nullable=False, default='[]'),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean, nullable=False, default=False),
    )
    op.create_index('ix_tenant_licenses_tenant_id', 'tenant_licenses', ['tenant_id'])

    # tenants tablosuna trial_expires_at kolonu
    op.add_column(
        'tenants',
        sa.Column('trial_expires_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('tenants', 'trial_expires_at')
    op.drop_table('tenant_licenses')
