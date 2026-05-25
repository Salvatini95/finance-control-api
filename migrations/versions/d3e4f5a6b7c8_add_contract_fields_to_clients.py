"""add contract fields to clients

Revision ID: d3e4f5a6b7c8
Revises: c290f1a3e8d5
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision      = 'd3e4f5a6b7c8'
down_revision = 'c290f1a3e8d5'
branch_labels = None
depends_on    = None


def upgrade():
    # Código interno do cliente
    op.add_column('clients', sa.Column('codigo',           sa.String(30),  nullable=True))
    # Dados fiscais
    op.add_column('clients', sa.Column('cnpj',             sa.String(30),  nullable=True))
    # Contrato
    op.add_column('clients', sa.Column('contrato_tipo',    sa.String(20),  nullable=True, server_default='avulso'))
    op.add_column('clients', sa.Column('contrato_valor',   sa.Float(),     nullable=True))
    op.add_column('clients', sa.Column('contrato_forma_pagamento', sa.String(30), nullable=True))
    op.add_column('clients', sa.Column('contrato_dia_pagamento',   sa.Integer(),  nullable=True))
    op.add_column('clients', sa.Column('contrato_inicio',  sa.String(20),  nullable=True))
    op.add_column('clients', sa.Column('contrato_fim',     sa.String(20),  nullable=True))
    op.add_column('clients', sa.Column('contrato_status',  sa.String(20),  nullable=True, server_default='ativo'))
    op.add_column('clients', sa.Column('contrato_dias_semana', sa.String(50), nullable=True))  # ex: "1,3,5" = seg,qua,sex
    op.add_column('clients', sa.Column('contrato_observacoes', sa.Text(),   nullable=True))


def downgrade():
    op.drop_column('clients', 'contrato_observacoes')
    op.drop_column('clients', 'contrato_dias_semana')
    op.drop_column('clients', 'contrato_status')
    op.drop_column('clients', 'contrato_fim')
    op.drop_column('clients', 'contrato_inicio')
    op.drop_column('clients', 'contrato_dia_pagamento')
    op.drop_column('clients', 'contrato_forma_pagamento')
    op.drop_column('clients', 'contrato_valor')
    op.drop_column('clients', 'contrato_tipo')
    op.drop_column('clients', 'cnpj')
    op.drop_column('clients', 'codigo')