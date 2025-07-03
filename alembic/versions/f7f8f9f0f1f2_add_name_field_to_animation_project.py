"""add name field to animation_projects and make animation_prompt nullable

Revision ID: f7f8f9f0f1f2
Revises: e1b2c3d4e5f6
Create Date: 2025-01-28 15:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f7f8f9f0f1f2'
down_revision = 'e1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade():
    # Add name column to animation_projects
    op.add_column('animation_projects', sa.Column('name', sa.String(255), nullable=False, server_default='Untitled Project'))
    
    # Make animation_prompt nullable
    op.alter_column('animation_projects', 'animation_prompt',
                    existing_type=sa.Text(),
                    nullable=True)

def downgrade():
    # Revert animation_prompt to not nullable
    op.alter_column('animation_projects', 'animation_prompt',
                    existing_type=sa.Text(),
                    nullable=False)
    
    # Drop name column
    op.drop_column('animation_projects', 'name') 