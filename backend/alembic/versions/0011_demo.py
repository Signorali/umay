"""Phase 5 — Demo sessions

Revision ID: 0011_demo
Revises: 0010_watchlist_source
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0011_demo"
down_revision: Union[str, None] = "0010_watchlist_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "demo_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seeded_modules", sa.String(500), nullable=True),
        sa.Column("seed_record_ids", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_demo_sessions_tenant", "demo_sessions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_demo_sessions_tenant", table_name="demo_sessions")
    op.drop_table("demo_sessions")
