"""Track accepted source proposals without changing existing tasks."""
from alembic import op
import sqlalchemy as sa

revision='7a0b2c3d4e5f'
down_revision='6a0b2c3d4e5f'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('tracked_checklist',sa.Column('proposal_key',sa.String(64),nullable=True))
    op.create_unique_constraint('uq_checklist_proposal','tracked_checklist',['scholarship_id','proposal_key'])

def downgrade():
    op.drop_constraint('uq_checklist_proposal','tracked_checklist',type_='unique')
    op.drop_column('tracked_checklist','proposal_key')
