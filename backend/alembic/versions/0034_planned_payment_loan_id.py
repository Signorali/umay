"""Add loan_id to planned_payments.

Revision ID: 0034_pp_loan_id
Revises: 0033_account_kmh_flag
Create Date: 2026-04-04 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0034_pp_loan_id'
down_revision = '0033_account_kmh_flag'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'planned_payments',
        sa.Column(
            'loan_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('loans.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('planned_payments', 'loan_id')
