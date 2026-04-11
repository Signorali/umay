"""Phase 4 — Dashboard widget configuration

Revision ID: 0007_dashboard
Revises: 0006_market_data
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007_dashboard"
down_revision: Union[str, None] = "0006_market_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dashboard_widgets",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("widget_type", sa.Text(), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("col_span", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("row_span", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_dashboard_widgets_user", "dashboard_widgets", ["user_id"])
    op.create_index("ix_dashboard_widgets_tenant", "dashboard_widgets", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_dashboard_widgets_tenant", table_name="dashboard_widgets")
    op.drop_index("ix_dashboard_widgets_user", table_name="dashboard_widgets")
    op.drop_table("dashboard_widgets")
