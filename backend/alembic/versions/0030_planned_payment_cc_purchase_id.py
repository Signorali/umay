"""Add credit_card_purchase_id to planned_payments.

Revision ID: 0030_pp_cc_purchase_id
Revises: 0029_cc_purchase_templates
Create Date: 2026-04-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0030_pp_cc_purchase_id'
down_revision = '0029_cc_purchase_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'planned_payments',
        sa.Column(
            'credit_card_purchase_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('credit_card_purchases.id', ondelete='SET NULL'),
            nullable=True,
        )
    )


def downgrade() -> None:
    op.drop_column('planned_payments', 'credit_card_purchase_id')
