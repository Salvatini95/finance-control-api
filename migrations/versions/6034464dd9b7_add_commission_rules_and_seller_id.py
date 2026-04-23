"""add commission_rules and seller_id to orders

Revision ID: add_commission_rules
Revises: 36e2d4953910
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Tabela de regras de comissão
    op.create_table(
        "commission_rules",
        sa.Column("id",         sa.Integer(),     nullable=False),
        sa.Column("seller_id",  sa.Integer(),     nullable=False),
        sa.Column("admin_id",   sa.Integer(),     nullable=False),
        sa.Column("company_id", sa.Integer(),     nullable=True),
        sa.Column("type",       sa.String(20),    nullable=False, server_default="percent_total"),
        sa.Column("value",      sa.Float(),       nullable=False, server_default="0"),
        sa.Column("active",     sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("created_at", sa.String(20),    nullable=True),
        sa.ForeignKeyConstraint(["seller_id"],  ["users.id"],     name="fk_commission_seller"),
        sa.ForeignKeyConstraint(["admin_id"],   ["users.id"],     name="fk_commission_admin"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_commission_company"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commission_rules_seller",  "commission_rules", ["seller_id"])
    op.create_index("ix_commission_rules_company", "commission_rules", ["company_id"])

    # 2. Campo seller_id no Order
    op.add_column("orders", sa.Column("seller_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_order_seller", "orders", "users", ["seller_id"], ["id"])

def downgrade():
    op.drop_constraint("fk_order_seller", "orders", type_="foreignkey")
    op.drop_column("orders", "seller_id")
    op.drop_index("ix_commission_rules_company", "commission_rules")
    op.drop_index("ix_commission_rules_seller",  "commission_rules")
    op.drop_table("commission_rules")