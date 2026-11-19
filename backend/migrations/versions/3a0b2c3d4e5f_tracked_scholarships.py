"""Add isolated URL-first tracking tables.

Revision ID: 3a0b2c3d4e5f
Revises: 2a0b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa

revision = '3a0b2c3d4e5f'
down_revision = '2a0b2c3d4e5f'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('tracked_scholarships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('url_key', sa.Text(), nullable=False, unique=True),
        sa.Column('title', sa.String(250)), sa.Column('provider', sa.String(250)),
        sa.Column('intake', sa.String(250)), sa.Column('deadline', sa.Date()),
        sa.Column('funding', sa.Text()), sa.Column('eligibility', sa.Text()), sa.Column('notes', sa.Text()),
        sa.Column('status', sa.String(20), nullable=False, server_default='saved'),
        sa.Column('archived_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('saved','preparing','submitted','accepted','rejected')", name='ck_tracked_status'))
    op.create_table('tracked_checklist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('scholarship_id', sa.Integer(), sa.ForeignKey('tracked_scholarships.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label', sa.String(250), nullable=False), sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index('ix_tracked_checklist_scholarship_id', 'tracked_checklist', ['scholarship_id'])

def downgrade():
    op.drop_table('tracked_checklist')
    op.drop_table('tracked_scholarships')
