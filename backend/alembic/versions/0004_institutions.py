"""Phase 3 — Institutions (banks, brokers, commission & tax rules)

Revision ID: 0004_institutions
Revises: 0003_assets
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_institutions"
down_revision: Union[str, None] = "0003_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("institution_type", sa.Text(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("swift_code", sa.String(20), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_institutions_tenant_id", "institutions", ["tenant_id"])

    op.create_table(
        "commission_rules",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("institution_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_type", sa.String(100), nullable=True),
        sa.Column("basis", sa.Text(), nullable=False, server_default="PERCENTAGE"),
        sa.Column("rate", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("min_amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("max_amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_commission_rules_institution_id", "commission_rules", ["institution_id"])

    op.create_table(
        "tax_rules",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("institution_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("rate", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("instrument_type", sa.String(100), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tax_rules_institution_id", "tax_rules", ["institution_id"])


def downgrade() -> None:
    op.drop_index("ix_tax_rules_institution_id", table_name="tax_rules")
    op.drop_table("tax_rules")
    op.drop_index("ix_commission_rules_institution_id", table_name="commission_rules")
    op.drop_table("commission_rules")
    op.drop_index("ix_institutions_tenant_id", table_name="institutions")
    op.drop_table("institutions")
