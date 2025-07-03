"""add progress columns to avatars and animation_segments

Revision ID: e1b2c3d4e5f6
Revises: d2d2a701d434
Create Date: 2025-07-02 13:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1b2c3d4e5f6'
down_revision = 'd2d2a701d434'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('avatars', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('animation_segments', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('animation_segments', 'progress')
    op.drop_column('avatars', 'progress') 