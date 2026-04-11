"""Add representative fields to institutions.

Revision ID: 0019_institution_rep
Revises: 0018_investment_account_link
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0019_institution_rep"
down_revision: Union[str, None] = "0018_investment_account_link"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("institutions", sa.Column("rep_name", sa.String(200), nullable=True))
    op.add_column("institutions", sa.Column("rep_phone", sa.String(50), nullable=True))
    op.add_column("institutions", sa.Column("rep_email", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("institutions", "rep_email")
    op.drop_column("institutions", "rep_phone")
    op.drop_column("institutions", "rep_name")
