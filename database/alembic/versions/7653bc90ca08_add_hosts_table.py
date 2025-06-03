from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision = 'your_new_revision_id'
down_revision = '11339dd7ff61'  # This must match the last migration's revision ID
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'hosts',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('remark', sa.String(255)),
        sa.Column('address', sa.String(255)),
        sa.Column('port', sa.Integer()),
        sa.Column('inbound_tag', sa.String(255)),
        sa.Column('sni', sa.String(255)),
        sa.Column('host', sa.String(255)),
        sa.Column('security', sa.String(255)),
        sa.Column('alpn', sa.String(255)),
        sa.Column('fingerprint', sa.String(255)),
        sa.Column('allowinsecure', sa.Boolean(), default=False),
        sa.Column('is_disabled', sa.Boolean(), default=False),
        sa.Column('path', sa.String(255)),
        sa.Column('mux_enable', sa.Boolean(), default=False),
        sa.Column('fragment_setting', sa.String(255)),
        sa.Column('random_user_agent', sa.Boolean(), default=False),
        sa.Column('noise_setting', sa.String(255)),
        sa.Column('use_sni_as_host', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

def downgrade():
    op.drop_table('hosts')
