"""Phase 4 — Documents (file metadata and financial linkage)

Revision ID: 0008_documents
Revises: 0007_dashboard
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0008_documents"
down_revision: Union[str, None] = "0007_dashboard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.Text(), nullable=False, server_default="OTHER"),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("stored_filename", sa.String(500), nullable=True),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("linked_transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_planned_payment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_loan_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_credit_card_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_asset_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("ocr_extracted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("ocr_draft_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_planned_payment_id"], ["planned_payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_loan_id"], ["loans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_credit_card_id"], ["credit_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_asset_id"], ["assets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_documents_tenant", "documents", ["tenant_id"])
    op.create_index("ix_documents_tx", "documents", ["linked_transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_documents_tx", table_name="documents")
    op.drop_index("ix_documents_tenant", table_name="documents")
    op.drop_table("documents")
