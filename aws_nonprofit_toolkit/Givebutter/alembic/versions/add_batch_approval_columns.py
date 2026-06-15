"""Add approval_status and override_details to import_batches for v1.1 review refinement.

Revision ID: add_batch_approval_v1_1
Revises: a9d993964dd4_update_schema_polymorphic_review_items_
Create Date: 2026-06-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_batch_approval_v1_1'
down_revision = 'a9d993964dd4_update_schema_polymorphic_review_items_'
branch_labels = None
depends_on = None


def upgrade():
    # Add approval_status column
    op.add_column('import_batches',
        sa.Column('approval_status', sa.String(50), nullable=True)
    )
    # Add override_details column
    op.add_column('import_batches',
        sa.Column('override_details', sa.JSON(), nullable=True)
    )


def downgrade():
    # Remove columns
    op.drop_column('import_batches', 'override_details')
    op.drop_column('import_batches', 'approval_status')
