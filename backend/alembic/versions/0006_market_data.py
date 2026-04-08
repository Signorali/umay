"""Phase 3 — Market data (providers, price snapshots, watchlists)

Revision ID: 0006_market_data
Revises: 0005_investments
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_market_data"
down_revision: Union[str, None] = "0005_investments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_providers",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("provider_type", sa.Text(), nullable=False, server_default="FREE_API"),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("api_key_ref", sa.String(200), nullable=True),
        sa.Column("supported_symbols", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("is_realtime", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_label", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["provider_id"], ["market_providers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_price_snapshots_symbol_time", "price_snapshots", ["symbol", "snapshot_at"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("instrument_type", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "symbol", name="uq_watchlist_user_symbol"),
    )
    op.create_index("ix_watchlist_tenant", "watchlist_items", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_watchlist_tenant", table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index("ix_price_snapshots_symbol_time", table_name="price_snapshots")
    op.drop_table("price_snapshots")
    op.drop_table("market_providers")
