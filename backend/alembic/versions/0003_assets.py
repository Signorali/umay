"""Phase 3 — Assets (real estate, vehicles, valuations)

Revision ID: 0003_assets
Revises: 0002_license_and_financial_core
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_assets"
down_revision: Union[str, None] = "0002_license_and_financial_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="OWNED"),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("purchase_value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("current_value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("sale_value", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("sale_notes", sa.Text(), nullable=True),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_assets_tenant_id", "assets", ["tenant_id"])
    op.create_index("ix_assets_group_id", "assets", ["group_id"])
    op.create_index("ix_assets_status", "assets", ["status"])

    op.create_table(
        "asset_valuations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("asset_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_asset_valuations_asset_id", "asset_valuations", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_asset_valuations_asset_id", table_name="asset_valuations")
    op.drop_table("asset_valuations")
    op.drop_index("ix_assets_status", table_name="assets")
    op.drop_index("ix_assets_group_id", table_name="assets")
    op.drop_index("ix_assets_tenant_id", table_name="assets")
    op.drop_table("assets")
