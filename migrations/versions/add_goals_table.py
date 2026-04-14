"""add goals table

Revision ID: a1b2c3d4e5f6
Revises: 273663341b72
Create Date: 2026-04-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '273663341b72'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('goals',
        sa.Column('id',          sa.Integer(),      nullable=False),
        sa.Column('name',        sa.String(200),    nullable=False),
        sa.Column('description', sa.String(500),    nullable=True),
        sa.Column('target',      sa.Float(),        nullable=False),
        sa.Column('current',     sa.Float(),        nullable=False, server_default='0'),
        sa.Column('category',    sa.String(100),    nullable=True),
        sa.Column('icon',        sa.String(10),     nullable=True,  server_default='🎯'),
        sa.Column('deadline',    sa.String(20),     nullable=True),
        sa.Column('status',      sa.String(20),     nullable=False, server_default='active'),
        sa.Column('created_at',  sa.String(20),     nullable=True),
        sa.Column('company_id',  sa.Integer(),      nullable=True),
        sa.Column('user_id',     sa.Integer(),      nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_goal_company'),
        sa.ForeignKeyConstraint(['user_id'],    ['users.id'],     name='fk_goal_user'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('goals')