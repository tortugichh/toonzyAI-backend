"""add_pending_registrations

Revision ID: add_pending_registrations
Revises: add_email_verification
Create Date: 2025-07-22 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

# revision identifiers, used by Alembic.
revision = 'add_pending_registrations'
down_revision = 'add_email_verification'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'pending_registrations',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('verification_token_expires', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('pending_registrations') 