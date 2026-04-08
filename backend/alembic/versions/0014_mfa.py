from alembic import op
import sqlalchemy as sa

revision = "0014_mfa"
down_revision = "0013_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "mfa_secret", sa.String(64), nullable=True, server_default=None
    ))
    op.add_column("users", sa.Column(
        "mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
    ))
    op.add_column("users", sa.Column(
        "mfa_backup_codes", sa.Text(), nullable=True, server_default=None
    ))


def downgrade() -> None:
    op.drop_column("users", "mfa_backup_codes")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "mfa_secret")
