"""Add reviewed source facts and source snapshots.

Revision ID: 2a0b2c3d4e5f
Revises: 1a0b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa
revision='2a0b2c3d4e5f'
down_revision='1a0b2c3d4e5f'
branch_labels=None
depends_on=None


def upgrade():
    for name in ('programme','intake','destination','degree','funding','eligibility','english','obligations','deadline_details','documents','application_steps','application_url'):
        op.add_column('applications', sa.Column(name, sa.Text(), nullable=True))
    op.create_table('application_sources',sa.Column('id',sa.Integer,primary_key=True),
        sa.Column('application_id',sa.Integer,sa.ForeignKey('applications.id',ondelete='CASCADE'),nullable=False),
        sa.Column('source_url',sa.Text),sa.Column('source_text',sa.Text,nullable=False),
        sa.Column('evidence_json',sa.Text,nullable=False),sa.Column('retrieved_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)))
    op.create_index('ix_application_sources_application_id','application_sources',['application_id'])


def downgrade():
    op.drop_table('application_sources')
    for name in ('programme','intake','destination','degree','funding','eligibility','english','obligations','deadline_details','documents','application_steps','application_url'):
        op.drop_column('applications',name)
