"""Add allow_negative_balance to accounts.

Revision ID: 0033_account_kmh_flag
Revises: 0032_asset_sale_tx_id
Create Date: 2026-04-04 07:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0033_account_kmh_flag'
down_revision = '0032_asset_sale_tx_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column(
            'allow_negative_balance',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'allow_negative_balance')
