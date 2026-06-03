# migrations/versions/nfse_order_fields_01.py
# Adiciona APENAS nfe_ref na tabela orders.
# As colunas nfe_chave, nfe_status, nfe_numero já existem no banco.
# A coluna token_focusnfe já existe na tabela companies.
# Esta migration só adiciona o que falta.

from alembic import op
import sqlalchemy as sa

revision      = "nfse_order_fields_01"
down_revision = "rg_limpeza_card_01"
branch_labels = None
depends_on    = None


def upgrade():
    # Única coluna nova — referência Focus NF-e para consulta e idempotência
    op.add_column("orders", sa.Column(
        "nfe_ref",
        sa.String(64),
        nullable=True,
    ))


def downgrade():
    op.drop_column("orders", "nfe_ref")