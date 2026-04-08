"""Add category_id to loans.

Revision ID: 0035_loan_category_id
Revises: 0034_pp_loan_id
Create Date: 2026-04-04 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0035_loan_category_id'
down_revision = '0034_pp_loan_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'loans',
        sa.Column(
            'category_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('categories.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('loans', 'category_id')
