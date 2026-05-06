"""add brand studio tables

Revision ID: add_brand_studio
Revises: add_fiscal_fields
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision      = 'add_brand_studio'
down_revision = 'add_fiscal_fields'
branch_labels = None
depends_on    = None


def upgrade():
    op.create_table(
        "brand_projects",
        sa.Column("id",          sa.Integer,     primary_key=True),
        sa.Column("name",        sa.String(200), nullable=False),
        sa.Column("canvas_data", sa.Text,        nullable=False, server_default="{}"),
        sa.Column("format",      sa.String(30),  nullable=False, server_default="insta_post"),
        sa.Column("created_at",  sa.String(20),  nullable=True),
        sa.Column("company_id",  sa.Integer,     sa.ForeignKey("companies.id", name="fk_brandproj_company"), nullable=True),
        sa.Column("user_id",     sa.Integer,     sa.ForeignKey("users.id",     name="fk_brandproj_user"),    nullable=False),
    )

    op.create_table(
        "brand_assets",
        sa.Column("id",         sa.Integer,     primary_key=True),
        sa.Column("filename",   sa.String(200), nullable=True),
        sa.Column("url",        sa.Text,        nullable=False),
        sa.Column("created_at", sa.String(20),  nullable=True),
        sa.Column("company_id", sa.Integer,     sa.ForeignKey("companies.id", name="fk_brandasset_company"), nullable=True),
        sa.Column("user_id",    sa.Integer,     sa.ForeignKey("users.id",     name="fk_brandasset_user"),    nullable=False),
    )


def downgrade():
    op.drop_table("brand_assets")
    op.drop_table("brand_projects")