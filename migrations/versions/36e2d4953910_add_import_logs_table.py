"""add import_logs table

Revision ID: 36e2d4953910
Revises: 8d4cd3fda368
Create Date: 2026-04-21 22:09:26.713308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '36e2d4953910'
down_revision = '8d4cd3fda368'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('import_logs',
    sa.Column('id',         sa.Integer(),      nullable=False),
    sa.Column('type',       sa.String(10),     nullable=False),
    sa.Column('entity',     sa.String(30),     nullable=False),
    sa.Column('sistema',    sa.String(30),     nullable=True),
    sa.Column('filename',   sa.String(200),    nullable=True),
    sa.Column('total',      sa.Integer(),      nullable=False, server_default='0'),
    sa.Column('created',    sa.Integer(),      nullable=False, server_default='0'),
    sa.Column('updated',    sa.Integer(),      nullable=False, server_default='0'),
    sa.Column('skipped',    sa.Integer(),      nullable=False, server_default='0'),
    sa.Column('errors',     sa.Integer(),      nullable=False, server_default='0'),
    sa.Column('errors_log', sa.Text(),         nullable=True),
    sa.Column('created_at', sa.String(30),     nullable=False, server_default=''),
    sa.Column('company_id', sa.Integer(),      nullable=True),
    sa.Column('user_id',    sa.Integer(),      nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_importlog_company'),
    sa.ForeignKeyConstraint(['user_id'],    ['users.id'],     name='fk_importlog_user'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('import_logs')