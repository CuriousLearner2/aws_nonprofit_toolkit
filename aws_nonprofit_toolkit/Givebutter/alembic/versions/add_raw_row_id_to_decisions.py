"""Add raw_import_row_id and make review_item_id nullable for row-level autosave.

Revision ID: add_raw_row_id_v1_1
Revises: add_batch_approval_v1_1
Create Date: 2026-06-13 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_raw_row_id_v1_1'
down_revision = 'add_batch_approval_v1_1'
branch_labels = None
depends_on = None


def upgrade():
    # Make review_item_id nullable
    op.alter_column('review_decisions', 'review_item_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # Add raw_import_row_id column
    op.add_column('review_decisions',
        sa.Column('raw_import_row_id', sa.Integer(), nullable=True)
    )
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_review_decisions_raw_import_row_id',
        'review_decisions', 'raw_import_rows',
        ['raw_import_row_id'], ['id']
    )


def downgrade():
    # Drop foreign key
    op.drop_constraint('fk_review_decisions_raw_import_row_id',
                      'review_decisions', type_='foreignkey')
    # Remove raw_import_row_id column
    op.drop_column('review_decisions', 'raw_import_row_id')
    # Make review_item_id not nullable
    op.alter_column('review_decisions', 'review_item_id',
               existing_type=sa.INTEGER(),
               nullable=False)
