"""Criação das tabelas Restaura Glass — cartão de serviço e ocorrências.

Revision ID: rg_limpeza_card_01
Revises: f1a2b3c4d5e6
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'rg_limpeza_card_01'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'limpeza_service_cards',
        sa.Column('id',           sa.Integer(),     nullable=False),
        sa.Column('company_id',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('order_id',     sa.Integer(),     nullable=False),
        sa.Column('client_id',    sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('frequencia',   sa.String(20),    nullable=False, server_default='semanal'),
        sa.Column('mes',          sa.Integer(),     nullable=False, server_default='1'),
        sa.Column('ano',          sa.Integer(),     nullable=False, server_default='2024'),
        sa.Column('dias_semana',  sa.String(3),     nullable=False, server_default='seg'),
        sa.Column('obs_contrato', sa.String(255),   nullable=True),
        sa.Column('semanas',      postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at',   sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at',   sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_limpeza_service_cards_company_id', 'limpeza_service_cards', ['company_id'], unique=False)
    op.create_index('ix_limpeza_service_cards_order_id',   'limpeza_service_cards', ['order_id'],   unique=True)

    op.create_table(
        'limpeza_occurrences',
        sa.Column('id',                 sa.Integer(),   nullable=False),
        sa.Column('company_id',         sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('order_id',           sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('user_id',            sa.Integer(),   nullable=True),
        sa.Column('tipo',               sa.String(30),  nullable=False, server_default=''),
        sa.Column('data',               sa.String(10),  nullable=False, server_default=''),
        sa.Column('hora',               sa.String(5),   nullable=True),
        sa.Column('reagendamento_data', sa.String(10),  nullable=True),
        sa.Column('reagendamento_hora', sa.String(5),   nullable=True),
        sa.Column('descricao',          sa.Text(),      nullable=True),
        sa.Column('created_at',         sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_limpeza_occurrences_company_id', 'limpeza_occurrences', ['company_id'], unique=False)
    op.create_index('ix_limpeza_occurrences_order_id',   'limpeza_occurrences', ['order_id'],   unique=False)


def downgrade():
    op.drop_index('ix_limpeza_occurrences_order_id',     table_name='limpeza_occurrences')
    op.drop_index('ix_limpeza_occurrences_company_id',   table_name='limpeza_occurrences')
    op.drop_table('limpeza_occurrences')

    op.drop_index('ix_limpeza_service_cards_order_id',   table_name='limpeza_service_cards')
    op.drop_index('ix_limpeza_service_cards_company_id', table_name='limpeza_service_cards')
    op.drop_table('limpeza_service_cards')