"""adiciona campos asaas na company e cria tabela subscriptions

Revision ID: billing_01
Revises: nfse_order_fields_01
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision      = "billing_01"
down_revision = "client_fields_v2_01"
branch_labels = None
depends_on    = None


def upgrade():
    # ── Novos campos na tabela companies ─────────────────────────────────────
    op.add_column("companies", sa.Column(
        "asaas_customer_id", sa.String(50), nullable=True
    ))
    op.add_column("companies", sa.Column(
        "trial_ends_at", sa.String(20), nullable=True
    ))
    op.add_column("companies", sa.Column(
        "plan_interval", sa.String(10), nullable=True, server_default="monthly"
    ))
    op.add_column("companies", sa.Column(
        "plan_locked_at", sa.String(20), nullable=True
    ))
    # Obs: campo `plan` já existe na tabela companies — não recriamos

    # ── Tabela subscriptions ──────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id",                  sa.Integer,     primary_key=True),
        sa.Column("company_id",          sa.Integer,     nullable=False),
        sa.Column("asaas_subscription_id", sa.String(50), nullable=True),
        sa.Column("asaas_customer_id",   sa.String(50),  nullable=True),
        sa.Column("plan",                sa.String(20),  nullable=False, server_default="free"),
        sa.Column("interval",            sa.String(10),  nullable=False, server_default="monthly"),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="trial"),
        sa.Column("valor",               sa.Float(),     nullable=False, server_default="0"),
        sa.Column("next_due_date",       sa.String(20),  nullable=True),
        sa.Column("trial_ends_at",       sa.String(20),  nullable=True),
        sa.Column("founder",             sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("billing_type",        sa.String(20),  nullable=False, server_default="PIX"),
        sa.Column("asaas_payment_id",    sa.String(50),  nullable=True),
        sa.Column("last_event",          sa.String(50),  nullable=True),
        sa.Column("last_event_at",       sa.String(30),  nullable=True),
        sa.Column("created_at",          sa.String(20),  nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_subscription_company"),
    )
    op.create_index("ix_subscriptions_company",  "subscriptions", ["company_id"])
    op.create_index("ix_subscriptions_status",   "subscriptions", ["status"])
    op.create_index("ix_subscriptions_asaas_id", "subscriptions", ["asaas_subscription_id"])


def downgrade():
    op.drop_index("ix_subscriptions_asaas_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status",   table_name="subscriptions")
    op.drop_index("ix_subscriptions_company",  table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_column("companies", "plan_locked_at")
    op.drop_column("companies", "plan_interval")
    op.drop_column("companies", "trial_ends_at")
    op.drop_column("companies", "asaas_customer_id")