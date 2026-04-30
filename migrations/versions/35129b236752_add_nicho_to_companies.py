"""add nicho to companies

Revision ID: 35129b236752
Revises: 6034464dd9b7
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '35129b236752'
down_revision = '6034464dd9b7'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column(
        'companies',
        sa.Column('nicho', sa.String(30), nullable=False, server_default='generic')
    )

def downgrade():
    op.drop_column('companies', 'nicho')