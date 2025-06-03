"""Add new column for is_updated

Revision ID: 11339dd7ff61
Revises: 83764ed9ba59
Create Date: 2024-05-25 23:40:13.143291

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '11339dd7ff61'
down_revision = '83764ed9ba59'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'telegram_users',
        sa.Column('is_updated', sa.Boolean())
    )


def downgrade():
    op.drop_column(
        'telegram_users',
        'is_updated'
    )
