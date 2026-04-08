"""credit_card_purchases_and_statement_lines

Revision ID: 0016
Revises: 0015_loan_payment_day
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0016"
down_revision = "0015_loan_payment_day"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CreditCardPurchase table
    op.create_table(
        "credit_card_purchases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("card_id", UUID(as_uuid=True), sa.ForeignKey("credit_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("installment_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("installment_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("purchase_date", sa.Date, nullable=False),
        sa.Column("remaining_installments", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
    )

    # CreditCardStatementLine table
    op.create_table(
        "credit_card_statement_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("statement_id", UUID(as_uuid=True), sa.ForeignKey("credit_card_statements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_id", UUID(as_uuid=True), sa.ForeignKey("credit_card_purchases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("line_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("installment_number", sa.Integer, nullable=True),
        sa.Column("total_installments", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
    )

    # Add new columns to credit_cards
    op.add_column("credit_cards", sa.Column("card_type", sa.String(50), nullable=False, server_default="CREDIT"))
    op.add_column("credit_cards", sa.Column("network", sa.String(50), nullable=False, server_default="VISA"))

    # Add new columns to credit_card_statements
    op.add_column("credit_card_statements", sa.Column("statement_closing_date", sa.Date, nullable=True))
    op.add_column("credit_card_statements", sa.Column("payment_account_id", UUID(as_uuid=True), nullable=True))
    op.add_column("credit_card_statements", sa.Column("payment_date", sa.Date, nullable=True))
    op.add_column("credit_card_statements", sa.Column("payment_transaction_id", UUID(as_uuid=True), nullable=True))
    op.add_column("credit_card_statements", sa.Column("theoretical_available", sa.Numeric(precision=20, scale=4), server_default="0", nullable=False))
    op.add_column("credit_card_statements", sa.Column("real_available", sa.Numeric(precision=20, scale=4), server_default="0", nullable=False))
    op.add_column("credit_card_statements", sa.Column("new_spending", sa.Numeric(precision=20, scale=4), server_default="0", nullable=False))

    # Add FK constraints for new statement columns
    op.create_foreign_key(
        "fk_statement_payment_account",
        "credit_card_statements", "accounts",
        ["payment_account_id"], ["id"],
        ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_statement_payment_transaction",
        "credit_card_statements", "transactions",
        ["payment_transaction_id"], ["id"],
        ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_statement_payment_transaction", "credit_card_statements", type_="foreignkey")
    op.drop_constraint("fk_statement_payment_account", "credit_card_statements", type_="foreignkey")
    op.drop_column("credit_card_statements", "new_spending")
    op.drop_column("credit_card_statements", "real_available")
    op.drop_column("credit_card_statements", "theoretical_available")
    op.drop_column("credit_card_statements", "payment_transaction_id")
    op.drop_column("credit_card_statements", "payment_date")
    op.drop_column("credit_card_statements", "payment_account_id")
    op.drop_column("credit_card_statements", "statement_closing_date")
    op.drop_column("credit_cards", "network")
    op.drop_column("credit_cards", "card_type")
    op.drop_table("credit_card_statement_lines")
    op.drop_table("credit_card_purchases")
