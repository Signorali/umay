"""institution_group_links: many-to-many groups per institution + institutions permissions

Revision ID: 0038_institution_group_links
Revises: 0037_asset_multi_links
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0038_institution_group_links'
down_revision = '0037_asset_multi_links'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'institution_group_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('institution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('institution_id', 'group_id', name='uq_institution_group_link'),
        sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_institution_group_links_institution_id', 'institution_group_links', ['institution_id'])
    op.create_index('ix_institution_group_links_group_id', 'institution_group_links', ['group_id'])

    # Seed institutions permissions
    op.execute("""
        INSERT INTO permissions (id, module, action, description)
        VALUES
          (gen_random_uuid(), 'institutions', 'view',   'Kurumları görüntüle'),
          (gen_random_uuid(), 'institutions', 'create', 'Kurum oluştur'),
          (gen_random_uuid(), 'institutions', 'update', 'Kurum güncelle'),
          (gen_random_uuid(), 'institutions', 'delete', 'Kurum sil')
        ON CONFLICT (module, action) DO NOTHING
    """)


def downgrade():
    op.drop_index('ix_institution_group_links_group_id', table_name='institution_group_links')
    op.drop_index('ix_institution_group_links_institution_id', table_name='institution_group_links')
    op.drop_table('institution_group_links')
    op.execute("DELETE FROM permissions WHERE module = 'institutions'")
