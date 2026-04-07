"""add source to transactions and transaction_id to orders

Revision ID: e48b4c9b4488
Revises: ba2d07c3615d
Create Date: 2026-03-31 13:53:10.728489

"""
from alembic import op
import sqlalchemy as sa

revision = 'e48b4c9b4488'
down_revision = 'ba2d07c3615d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('transaction_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(length=20), nullable=False, server_default='manual'))


def downgrade():
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('source')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('transaction_id')