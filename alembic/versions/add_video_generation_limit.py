"""add video generation limit

Revision ID: add_video_generation_limit
Revises: f7f8f9f0f1f2
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_video_generation_limit'
down_revision = 'f7f8f9f0f1f2'
branch_labels = None
depends_on = None


def upgrade():
    # Add video_generation_count column to users table
    op.add_column('users', sa.Column('video_generation_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    # Remove video_generation_count column from users table
    op.drop_column('users', 'video_generation_count') 