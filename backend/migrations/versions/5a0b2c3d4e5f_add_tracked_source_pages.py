"""Add additional official source pages.

Revision ID: 5a0b2c3d4e5f
Revises: 4a0b2c3d4e5f
"""
from alembic import op
import sqlalchemy as sa

revision='5a0b2c3d4e5f'
down_revision='4a0b2c3d4e5f'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table(
        'tracked_source_pages',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('scholarship_id',sa.Integer(),sa.ForeignKey('tracked_scholarships.id',ondelete='CASCADE'),nullable=False),
        sa.Column('source_url',sa.Text(),nullable=False),
        sa.Column('url_key',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
        sa.CheckConstraint("source_url LIKE 'https://%'",name='ck_tracked_source_https'),
        sa.UniqueConstraint('scholarship_id','url_key',name='uq_tracked_source_page_url'),
    )
    op.create_index('ix_tracked_source_pages_scholarship_id','tracked_source_pages',['scholarship_id'])


def downgrade():
    op.drop_table('tracked_source_pages')
