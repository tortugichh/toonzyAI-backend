"""merge heads

Revision ID: 6ef27f478590
Revises: add_email_verification, update_stories_struct
Create Date: 2025-07-21 05:40:49.566614

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ef27f478590'
down_revision = ('add_email_verification', 'update_stories_struct')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass