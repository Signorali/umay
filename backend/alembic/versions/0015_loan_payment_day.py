"""Add payment_day and installment_amount to loans

Revision ID: 0015_loan_payment_day
Revises: 0014_mfa
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa

revision = '0015_loan_payment_day'
down_revision = '0014_mfa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Using raw SQL with IF NOT EXISTS to handle manual emergency hotfix state
    op.execute("ALTER TABLE loans ADD COLUMN IF NOT EXISTS payment_day INTEGER")
    op.execute("ALTER TABLE loans ADD COLUMN IF NOT EXISTS installment_amount NUMERIC(20,4)")
    
    # Ensure values are backfilled if they were null (optional with IF NOT EXISTS but safe)
    op.execute("UPDATE loans SET payment_day = 1 WHERE payment_day IS NULL")
    op.execute("UPDATE loans SET installment_amount = 0 WHERE installment_amount IS NULL")



def downgrade() -> None:
    op.drop_column('loans', 'installment_amount')
    op.drop_column('loans', 'payment_day')
