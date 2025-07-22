"""merge heads for pending registrations

Revision ID: 1ffe2191358d
Revises: 6ef27f478590, add_pending_registrations
Create Date: 2025-07-22 08:31:58.018550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1ffe2191358d'
down_revision = ('6ef27f478590', 'add_pending_registrations')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass