"""Add personal application tracker without changing catalogue tables.

Revision ID: 1a0b2c3d4e5f
Revises: de4ceda7784b
"""
from alembic import op
import sqlalchemy as sa

revision = '1a0b2c3d4e5f'
down_revision = 'de4ceda7784b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('applications', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('title', sa.String(250), nullable=False), sa.Column('provider', sa.String(250)),
        sa.Column('source_url', sa.Text), sa.Column('cycle', sa.String(100)),
        sa.Column('status', sa.String(30), nullable=False, server_default='researching'),
        sa.Column('notes', sa.Text), sa.Column('next_action', sa.Text),
        sa.Column('archived', sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column('submission_date', sa.Date), sa.Column('interview_date', sa.Date), sa.Column('outcome', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('researching','preparing','submitted','result_received','withdrawn')", name='ck_application_status'))
    op.create_table('application_deadlines', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('application_id', sa.Integer, sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('label', sa.String(250), nullable=False), sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('due_date', sa.Date), sa.Column('due_time', sa.String(20)), sa.Column('timezone', sa.String(100)),
        sa.CheckConstraint("kind IN ('official','personal')", name='ck_deadline_kind'))
    op.create_index('ix_application_deadlines_application_id','application_deadlines',['application_id'])
    op.create_table('application_tasks', sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('application_id', sa.Integer, sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(250), nullable=False), sa.Column('due_date', sa.Date),
        sa.Column('completed', sa.Boolean, nullable=False, server_default=sa.false()))
    op.create_index('ix_application_tasks_application_id','application_tasks',['application_id'])


def downgrade():
    op.drop_table('application_tasks')
    op.drop_table('application_deadlines')
    op.drop_table('applications')
