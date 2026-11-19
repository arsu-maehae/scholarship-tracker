"""Add bounded extraction attempts.

Revision ID: 4a0b2c3d4e5f
Revises: 3a0b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa

revision='4a0b2c3d4e5f'
down_revision='3a0b2c3d4e5f'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('extraction_attempts',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('scholarship_id',sa.Integer(),sa.ForeignKey('tracked_scholarships.id',ondelete='CASCADE'),nullable=False),
        sa.Column('input_kind',sa.String(10),nullable=False),sa.Column('source_url',sa.Text()),
        sa.Column('outcome',sa.String(20),nullable=False),sa.Column('suggestions_json',sa.Text(),nullable=False,server_default='{}'),
        sa.Column('attempted_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()))
    op.create_index('ix_extraction_attempts_scholarship_id','extraction_attempts',['scholarship_id'])

def downgrade():
    op.drop_table('extraction_attempts')
