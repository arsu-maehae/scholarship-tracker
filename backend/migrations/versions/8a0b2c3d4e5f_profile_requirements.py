"""Add a local student profile and reviewed source requirements."""
from alembic import op
import sqlalchemy as sa

revision='8a0b2c3d4e5f'
down_revision='7a0b2c3d4e5f'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('student_profile',sa.Column('id',sa.Integer,primary_key=True),*[sa.Column(name,sa.String(120),nullable=True) for name in ('nationality','prior_degree','field','target_intake','language_status')],sa.CheckConstraint('id = 1',name='ck_single_student_profile'))
    op.create_table('reviewed_requirements',sa.Column('id',sa.Integer,primary_key=True),sa.Column('scholarship_id',sa.Integer,sa.ForeignKey('tracked_scholarships.id',ondelete='CASCADE'),nullable=False),sa.Column('source_url',sa.Text,nullable=False),sa.Column('excerpt',sa.Text,nullable=False),sa.Column('kind',sa.String(30),nullable=False),sa.Column('expected',sa.String(120),nullable=False))
    op.create_index('ix_reviewed_requirements_scholarship_id','reviewed_requirements',['scholarship_id'])

def downgrade():
    op.drop_table('reviewed_requirements')
    op.drop_table('student_profile')
