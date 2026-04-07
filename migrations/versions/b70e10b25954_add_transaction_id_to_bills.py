"""add transaction_id to bills

Revision ID: b70e10b25954
Revises: 1387e593bc6e
Create Date: 2026-03-30 22:01:00.736294

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b70e10b25954'
down_revision = '1387e593bc6e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.add_column(sa.Column('transaction_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.drop_column('transaction_id')