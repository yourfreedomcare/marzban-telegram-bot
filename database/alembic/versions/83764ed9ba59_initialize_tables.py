"""Initialize tables

Revision ID: 83764ed9ba59
Revises: 
Create Date: 2024-05-24 17:30:22.572311

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '83764ed9ba59'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('telegram_users',
        sa.Column('telegram_user_id', sa.String(255), primary_key=True),
        sa.Column('chat_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), default=func.now()),
        sa.Column('updated_at', sa.DateTime(), default=func.now(), onupdate=func.now())
    )

    op.create_table('telegram_users_configurations',
        sa.Column('id', sa.Integer(), primary_key=True, auto_increment = True),
        sa.Column('vless_link', sa.String(8000)),
        sa.Column('telegram_user_id', sa.String(255), sa.ForeignKey('telegram_users.telegram_user_id', ondelete='CASCADE')),
        sa.Column('created_at', sa.DateTime(), default=func.now()),
        sa.Column('updated_at', sa.DateTime(), default=func.now(), onupdate=func.now())
    )

def downgrade():
    op.drop_table('telegram_users_configurations')
    op.drop_table('telegram_users')
