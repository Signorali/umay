"""Add fx_rate, source_account_id, loan_id to assets.

Revision ID: 0031_asset_src_loan_fx
Revises: 0030_pp_cc_purchase_id
Create Date: 2026-04-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0031_asset_src_loan_fx'
down_revision = '0030_pp_cc_purchase_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'assets',
        sa.Column('fx_rate', sa.Numeric(precision=20, scale=8), nullable=False, server_default='1'),
    )
    op.add_column(
        'assets',
        sa.Column(
            'source_account_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('accounts.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column(
        'assets',
        sa.Column(
            'loan_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('loans.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('assets', 'loan_id')
    op.drop_column('assets', 'source_account_id')
    op.drop_column('assets', 'fx_rate')
