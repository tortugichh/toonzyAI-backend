"""update stories table structure

Revision ID: update_stories_struct
Revises: 133dda99c33f
Create Date: 2025-01-29 12:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_stories_struct'
down_revision = '133dda99c33f'
branch_labels = None
depends_on = None

def upgrade():
    # Create enum type first
    op.execute("CREATE TYPE storystatus AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')")
    
    # Add new columns
    op.add_column('stories', sa.Column('prompt', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('genre', sa.String(length=100), nullable=True))
    op.add_column('stories', sa.Column('style', sa.String(length=100), nullable=True))
    op.add_column('stories', sa.Column('theme', sa.String(length=255), nullable=True))
    op.add_column('stories', sa.Column('book_style', sa.String(length=100), nullable=True))
    op.add_column('stories', sa.Column('wishes', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('task_id', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('stories', sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='storystatus'), nullable=False, server_default='PENDING'))
    op.add_column('stories', sa.Column('story_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Make title nullable since we now have theme and prompt
    op.alter_column('stories', 'title', nullable=True)
    
    # Add unique constraint on task_id
    op.create_unique_constraint('uq_stories_task_id', 'stories', ['task_id'])
    
    # Drop old columns
    op.drop_column('stories', 'script_data')
    op.drop_column('stories', 'style_data')
    op.drop_column('stories', 'characters_data')
    op.drop_column('stories', 'environments_data')
    op.drop_column('stories', 'illustrations_data')
    op.drop_column('stories', 'quiz_data')

def downgrade():
    # Add back old columns
    op.add_column('stories', sa.Column('script_data', sa.Text(), nullable=False))
    op.add_column('stories', sa.Column('style_data', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('characters_data', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('environments_data', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('illustrations_data', sa.Text(), nullable=True))
    op.add_column('stories', sa.Column('quiz_data', sa.Text(), nullable=True))
    
    # Drop new columns
    op.drop_constraint('uq_stories_task_id', 'stories', type_='unique')
    op.drop_column('stories', 'story_data')
    op.drop_column('stories', 'status')
    op.drop_column('stories', 'task_id')
    op.drop_column('stories', 'wishes')
    op.drop_column('stories', 'book_style')
    op.drop_column('stories', 'theme')
    op.drop_column('stories', 'style')
    op.drop_column('stories', 'genre')
    op.drop_column('stories', 'prompt')
    
    # Make title required again
    op.alter_column('stories', 'title', nullable=False)
    
    # Drop enum type
    op.execute("DROP TYPE storystatus") 