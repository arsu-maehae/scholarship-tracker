"""Add optional due dates to tracked checklist items.

Revision ID: 6a0b2c3d4e5f
Revises: 5a0b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa

revision='6a0b2c3d4e5f'
down_revision='5a0b2c3d4e5f'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('tracked_checklist',sa.Column('due_date',sa.Date(),nullable=True))


def downgrade():
    op.drop_column('tracked_checklist','due_date')
