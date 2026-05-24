"""add service checkins

Revision ID: 90ea88b8fd49
Revises: e48b4c9b4488
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '90ea88b8fd49'
down_revision = 'add_brand_studio'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'service_checkins',
        sa.Column('id',          sa.Integer(),    nullable=False),
        sa.Column('executed_at', sa.String(30),   nullable=False),
        sa.Column('latitude',    sa.Float(),      nullable=True),
        sa.Column('longitude',   sa.Float(),      nullable=True),
        sa.Column('notes',       sa.Text(),       nullable=True),
        sa.Column('client_id',   sa.Integer(),    nullable=False),
        sa.Column('user_id',     sa.Integer(),    nullable=False),
        sa.Column('company_id',  sa.Integer(),    nullable=False),
        sa.ForeignKeyConstraint(['client_id'],  ['clients.id'],   name='fk_checkin_client'),
        sa.ForeignKeyConstraint(['user_id'],    ['users.id'],     name='fk_checkin_user'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_checkin_company'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_checkins_company',     'service_checkins', ['company_id'])
    op.create_index('ix_checkins_client',      'service_checkins', ['client_id'])
    op.create_index('ix_checkins_user',        'service_checkins', ['user_id'])
    op.create_index('ix_checkins_executed_at', 'service_checkins', ['executed_at'])


def downgrade():
    op.drop_index('ix_checkins_executed_at', table_name='service_checkins')
    op.drop_index('ix_checkins_user',        table_name='service_checkins')
    op.drop_index('ix_checkins_client',      table_name='service_checkins')
    op.drop_index('ix_checkins_company',     table_name='service_checkins')
    op.drop_table('service_checkins')