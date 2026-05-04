"""add fiscal fields for nfe

Revision ID: add_fiscal_fields
Revises: 35129b236752
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa

revision      = 'add_fiscal_fields'
down_revision = '35129b236752'
branch_labels = None
depends_on    = None


def upgrade():
    # ── Company — campos fiscais + endereço + token Focus ──
    op.add_column("companies", sa.Column("inscricao_estadual",  sa.String(30),  nullable=True))
    op.add_column("companies", sa.Column("inscricao_municipal", sa.String(30),  nullable=True))
    op.add_column("companies", sa.Column("regime_tributario",   sa.String(2),   nullable=True, server_default="1"))
    op.add_column("companies", sa.Column("cep",                 sa.String(10),  nullable=True))
    op.add_column("companies", sa.Column("logradouro",          sa.String(200), nullable=True))
    op.add_column("companies", sa.Column("numero",              sa.String(20),  nullable=True))
    op.add_column("companies", sa.Column("complemento",         sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("bairro",              sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("municipio",           sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("uf",                  sa.String(2),   nullable=True))
    op.add_column("companies", sa.Column("codigo_municipio",    sa.String(10),  nullable=True))
    op.add_column("companies", sa.Column("telefone",            sa.String(20),  nullable=True))
    op.add_column("companies", sa.Column("token_focusnfe",      sa.String(100), nullable=True))

    # ── Product — campos fiscais ──
    op.add_column("products", sa.Column("ncm",        sa.String(10), nullable=True))
    op.add_column("products", sa.Column("cfop",       sa.String(10), nullable=True))
    op.add_column("products", sa.Column("cst_icms",   sa.String(5),  nullable=True))
    op.add_column("products", sa.Column("csosn",      sa.String(5),  nullable=True))
    op.add_column("products", sa.Column("cst_pis",    sa.String(5),  nullable=True, server_default="07"))
    op.add_column("products", sa.Column("cst_cofins", sa.String(5),  nullable=True, server_default="07"))
    op.add_column("products", sa.Column("origem",     sa.String(2),  nullable=True, server_default="0"))

    # ── Client — endereço fiscal ──
    op.add_column("clients", sa.Column("inscricao_estadual", sa.String(30),  nullable=True))
    op.add_column("clients", sa.Column("cep",                sa.String(10),  nullable=True))
    op.add_column("clients", sa.Column("logradouro",         sa.String(200), nullable=True))
    op.add_column("clients", sa.Column("numero",             sa.String(20),  nullable=True))
    op.add_column("clients", sa.Column("complemento",        sa.String(100), nullable=True))
    op.add_column("clients", sa.Column("bairro",             sa.String(100), nullable=True))
    op.add_column("clients", sa.Column("municipio",          sa.String(100), nullable=True))
    op.add_column("clients", sa.Column("uf",                 sa.String(2),   nullable=True))
    op.add_column("clients", sa.Column("codigo_municipio",   sa.String(10),  nullable=True))

    # ── Order — dados da NF-e emitida ──
    op.add_column("orders", sa.Column("nfe_chave",  sa.String(50), nullable=True))
    op.add_column("orders", sa.Column("nfe_status", sa.String(20), nullable=True))
    op.add_column("orders", sa.Column("nfe_numero", sa.String(10), nullable=True))


def downgrade():
    # Order
    op.drop_column("orders", "nfe_numero")
    op.drop_column("orders", "nfe_status")
    op.drop_column("orders", "nfe_chave")

    # Client
    op.drop_column("clients", "codigo_municipio")
    op.drop_column("clients", "uf")
    op.drop_column("clients", "municipio")
    op.drop_column("clients", "bairro")
    op.drop_column("clients", "complemento")
    op.drop_column("clients", "numero")
    op.drop_column("clients", "logradouro")
    op.drop_column("clients", "cep")
    op.drop_column("clients", "inscricao_estadual")

    # Product
    op.drop_column("products", "origem")
    op.drop_column("products", "cst_cofins")
    op.drop_column("products", "cst_pis")
    op.drop_column("products", "csosn")
    op.drop_column("products", "cst_icms")
    op.drop_column("products", "cfop")
    op.drop_column("products", "ncm")

    # Company
    op.drop_column("companies", "token_focusnfe")
    op.drop_column("companies", "telefone")
    op.drop_column("companies", "codigo_municipio")
    op.drop_column("companies", "uf")
    op.drop_column("companies", "municipio")
    op.drop_column("companies", "bairro")
    op.drop_column("companies", "complemento")
    op.drop_column("companies", "numero")
    op.drop_column("companies", "logradouro")
    op.drop_column("companies", "cep")
    op.drop_column("companies", "regime_tributario")
    op.drop_column("companies", "inscricao_municipal")
    op.drop_column("companies", "inscricao_estadual")