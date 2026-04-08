"""Phase 4 — OCR drafts (AI extraction, human-confirmed only)

Revision ID: 0009_ocr_drafts
Revises: 0008_documents
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0009_ocr_drafts"
down_revision: Union[str, None] = "0008_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocr_drafts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("suggested_amount", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("suggested_currency", sa.String(10), nullable=True),
        sa.Column("suggested_date", sa.Date(), nullable=True),
        sa.Column("suggested_description", sa.String(500), nullable=True),
        sa.Column("suggested_category_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_transaction_type", sa.String(20), nullable=True),
        sa.Column("raw_extraction", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("reviewed_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("accepted_transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["accepted_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ocr_drafts_tenant", "ocr_drafts", ["tenant_id"])
    op.create_index("ix_ocr_drafts_status", "ocr_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ocr_drafts_status", table_name="ocr_drafts")
    op.drop_index("ix_ocr_drafts_tenant", table_name="ocr_drafts")
    op.drop_table("ocr_drafts")
