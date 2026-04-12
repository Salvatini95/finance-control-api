"""add account_type to users

Revision ID: 273663341b72
Revises: bed3b2c9bb31
Create Date: 2026-04-12 12:27:15.062191

"""
from alembic import op
import sqlalchemy as sa


revision = '273663341b72'
down_revision = 'bed3b2c9bb31'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_type', sa.String(length=20), nullable=False, server_default='business'))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('account_type')