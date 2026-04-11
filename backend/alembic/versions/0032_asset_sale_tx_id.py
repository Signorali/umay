"""Add sale_transaction_id to assets.

Revision ID: 0032_asset_sale_tx_id
Revises: 0031_asset_src_loan_fx
Create Date: 2026-04-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0032_asset_sale_tx_id'
down_revision = '0031_asset_src_loan_fx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'assets',
        sa.Column(
            'sale_transaction_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('transactions.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('assets', 'sale_transaction_id')
