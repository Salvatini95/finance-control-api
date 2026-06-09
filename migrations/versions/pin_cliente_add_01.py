"""adiciona pin_cliente na tabela clients

Revision ID: pin_cliente_add_01
Revises: client_fields_v2_01
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision      = 'pin_cliente_add_01'
down_revision = 'client_fields_v2_01'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('clients', sa.Column('pin_cliente', sa.String(10), nullable=True))
    op.create_index('ix_clients_pin_cliente', 'clients', ['company_id', 'pin_cliente'])


def downgrade():
    op.drop_index('ix_clients_pin_cliente', table_name='clients')
    op.drop_column('clients', 'pin_cliente')