"""add latitude longitude to clients

Revision ID: c290f1a3e8d5
Revises: b178351bbac2
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision    = 'c290f1a3e8d5'
down_revision = 'b178351bbac2'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('clients', sa.Column('latitude',  sa.Float(), nullable=True))
    op.add_column('clients', sa.Column('longitude', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('clients', 'longitude')
    op.drop_column('clients', 'latitude')