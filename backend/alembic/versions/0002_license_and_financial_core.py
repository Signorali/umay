"""Phase 1 close + Phase 2 financial core schema

Revision ID: 0002_license_and_financial_core
Revises: 0001_initial_schema
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_license_and_financial_core"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # license_records
    op.create_table(
        "license_records",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("license_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("license_key", sa.String(512), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_groups", sa.Integer(), nullable=True),
        sa.Column("max_tenants", sa.Integer(), nullable=True),
        sa.Column("machine_id", sa.String(255), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("holder_name", sa.String(255), nullable=True),
        sa.Column("holder_email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_type", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("opening_balance", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("current_balance", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("institution_name", sa.String(200), nullable=True),
        sa.Column("iban", sa.String(50), nullable=True),
        sa.Column("account_number", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("include_in_total", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_group_id", "accounts", ["group_id"])

    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category_type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"])

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT"),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("source_account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("target_account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("reversed_by_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("reversal_of_id", sa.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversed_by_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversal_of_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tx_tenant_date", "transactions", ["tenant_id", "transaction_date"])
    op.create_index("ix_tx_group_date", "transactions", ["group_id", "transaction_date"])

    # transaction_tags
    op.create_table(
        "transaction_tags",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("transaction_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
    )

    # ledger_entries
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("transaction_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_ledger_transaction", "ledger_entries", ["transaction_id"])
    op.create_index("ix_ledger_account_posted", "ledger_entries", ["account_id", "posted_at"])

    # planned_payments
    op.create_table(
        "planned_payments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("paid_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("category_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("reminder_date", sa.Date(), nullable=True),
        sa.Column("recurrence_rule", sa.Text(), nullable=False, server_default="NONE"),
        sa.Column("recurrence_end_date", sa.Date(), nullable=True),
        sa.Column("recurrence_count", sa.Integer(), nullable=True),
        sa.Column("total_installments", sa.Integer(), nullable=True),
        sa.Column("current_installment", sa.Integer(), nullable=True),
        sa.Column("parent_planned_payment_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("linked_transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_planned_payment_id"], ["planned_payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_planned_payments_tenant_id", "planned_payments", ["tenant_id"])

    # loans
    op.create_table(
        "loans",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("lender_name", sa.String(300), nullable=False),
        sa.Column("loan_purpose", sa.String(500), nullable=True),
        sa.Column("principal", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("disbursed_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("interest_rate", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("total_interest", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("fees", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("total_paid", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("remaining_balance", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_loans_tenant_id", "loans", ["tenant_id"])

    # loan_installments
    op.create_table(
        "loan_installments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("loan_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("principal_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("interest_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("paid_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("linked_transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )

    # credit_cards
    op.create_table(
        "credit_cards",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("card_name", sa.String(200), nullable=False),
        sa.Column("bank_name", sa.String(200), nullable=False),
        sa.Column("last_four_digits", sa.String(4), nullable=True),
        sa.Column("credit_limit", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("current_debt", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("statement_day", sa.Integer(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("expiry_month", sa.Integer(), nullable=True),
        sa.Column("expiry_year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_account_id"], ["accounts.id"], ondelete="SET NULL"),
    )

    # credit_card_statements
    op.create_table(
        "credit_card_statements",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("card_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="OPEN"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("total_spending", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("minimum_payment", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(precision=20, scale=4), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["card_id"], ["credit_cards.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("credit_card_statements")
    op.drop_table("credit_cards")
    op.drop_table("loan_installments")
    op.drop_table("loans")
    op.drop_index("ix_planned_payments_tenant_id", table_name="planned_payments")
    op.drop_table("planned_payments")
    op.drop_index("ix_ledger_account_posted", table_name="ledger_entries")
    op.drop_index("ix_ledger_transaction", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_table("transaction_tags")
    op.drop_index("ix_tx_group_date", table_name="transactions")
    op.drop_index("ix_tx_tenant_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_categories_tenant_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_accounts_group_id", table_name="accounts")
    op.drop_index("ix_accounts_tenant_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("license_records")
