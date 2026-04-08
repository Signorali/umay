"""Add created_by_user_id to transactions, must_change_password to users, delete_requests table

Revision ID: 0025_permissions_delete_requests
Revises: 0024_user_prefs_watchlist_state
Create Date: 2026-04-02
"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = '0025_permissions_delete_requests'
down_revision = '0024_user_prefs_watchlist_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users: must_change_password flag ---
    op.add_column('users', sa.Column(
        'must_change_password', sa.Boolean(), nullable=False, server_default='false'
    ))

    # --- transactions: who created it ---
    op.add_column('transactions', sa.Column(
        'created_by_user_id',
        sa.UUID(as_uuid=True),
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.create_index('ix_transactions_created_by', 'transactions', ['created_by_user_id'])

    # --- delete_requests table ---
    op.create_table(
        'delete_requests',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_by_user_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_table', sa.String(100), nullable=False),
        sa.Column('target_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('target_label', sa.String(500), nullable=True),  # human-readable description
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by_user_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reject_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.CheckConstraint("status IN ('pending','approved','rejected')",
                           name='chk_delete_request_status'),
    )
    op.create_index('ix_delete_requests_tenant_id', 'delete_requests', ['tenant_id'])
    op.create_index('ix_delete_requests_tenant_status', 'delete_requests', ['tenant_id', 'status'])
    op.create_index('ix_delete_requests_target', 'delete_requests', ['target_table', 'target_id'])
    op.create_index('ix_delete_requests_requester', 'delete_requests', ['requested_by_user_id'])


def downgrade() -> None:
    op.drop_table('delete_requests')
    op.drop_index('ix_transactions_created_by', 'transactions')
    op.drop_column('transactions', 'created_by_user_id')
    op.drop_column('users', 'must_change_password')
