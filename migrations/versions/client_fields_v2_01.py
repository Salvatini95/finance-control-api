"""Adiciona emails_json, phones_json, recorrencia, contrato_modelo e codigo_seq ao Client

Revision ID: client_fields_v2_01
Revises: nfse_order_fields_01
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision      = "client_fields_v2_01"
down_revision = "nfse_order_fields_01"
branch_labels = None
depends_on    = None


def upgrade():
    # emails e telefones múltiplos — JSON em texto (compatível com todos os deploys)
    op.add_column("clients", sa.Column("emails_json",      sa.Text(),    nullable=True))
    op.add_column("clients", sa.Column("phones_json",      sa.Text(),    nullable=True))

    # recorrência separada do tipo de contrato
    op.add_column("clients", sa.Column("recorrencia",      sa.String(20), nullable=True))

    # modelo/texto livre do contrato
    op.add_column("clients", sa.Column("contrato_modelo",  sa.Text(),    nullable=True))

    # código sequencial numérico por empresa (gerado automaticamente)
    op.add_column("clients", sa.Column("codigo_seq",       sa.Integer(), nullable=True))

    # índice para busca rápida de código por empresa
    op.create_index("ix_clients_company_codigo_seq", "clients", ["company_id", "codigo_seq"])


def downgrade():
    op.drop_index("ix_clients_company_codigo_seq", table_name="clients")
    op.drop_column("clients", "codigo_seq")
    op.drop_column("clients", "contrato_modelo")
    op.drop_column("clients", "recorrencia")
    op.drop_column("clients", "phones_json")
    op.drop_column("clients", "emails_json")