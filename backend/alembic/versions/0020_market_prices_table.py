"""Create market_prices table (was missing from 0005_investments).

Revision ID: 0020_market_prices
Revises: 0019_institution_rep
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0020_market_prices"
down_revision: Union[str, None] = "0019_institution_rep"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_prices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("name", sa.String(300), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False,
                  server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="TRY"),
        sa.Column("last_updated", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("source_symbol", sa.String(100), nullable=True),
        sa.UniqueConstraint("tenant_id", "symbol", name="uq_market_price_tenant_symbol"),
    )


def downgrade() -> None:
    op.drop_table("market_prices")
