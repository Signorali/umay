"""Phase 4 — Calendar sync (calendar items and sync logs)

Revision ID: 0010_calendar_sync
Revises: 0009_market_price_change
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010_calendar_sync"
down_revision: Union[str, None] = "0009_market_price_change"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("linked_planned_payment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_loan_installment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_credit_card_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_planned_payment_id"], ["planned_payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_loan_installment_id"], ["loan_installments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_credit_card_id"], ["credit_cards.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_calendar_items_user", "calendar_items", ["user_id", "due_date"])
    op.create_index("ix_calendar_items_tenant", "calendar_items", ["tenant_id"])

    op.create_table(
        "calendar_sync_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("sync_type", sa.String(100), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("items_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_cal_sync_logs_tenant", "calendar_sync_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_cal_sync_logs_tenant", table_name="calendar_sync_logs")
    op.drop_table("calendar_sync_logs")
    op.drop_index("ix_calendar_items_tenant", table_name="calendar_items")
    op.drop_index("ix_calendar_items_user", table_name="calendar_items")
    op.drop_table("calendar_items")
