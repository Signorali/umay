"""Add sensitive fields to credit_cards

Revision ID: 0042
Revises: 0041
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa


revision = '0042'
down_revision = '0041'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('credit_cards', sa.Column('card_number_encrypted', sa.Text(), nullable=True))
    op.add_column('credit_cards', sa.Column('cvv_encrypted', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('credit_cards', 'cvv_encrypted')
    op.drop_column('credit_cards', 'card_number_encrypted')
