"""add checkin checkout fields to service_checkins

Revision ID: b2c3d4e5f6a7
Revises: 90ea88b8fd49
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'b178351bbac2'
down_revision = '90ea88b8fd49'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona campos de check-in/check-out e vínculo com OS
    op.add_column('service_checkins', sa.Column('checkin_at',   sa.String(30), nullable=True))
    op.add_column('service_checkins', sa.Column('checkout_at',  sa.String(30), nullable=True))
    op.add_column('service_checkins', sa.Column('duration_min', sa.Integer(),  nullable=True))
    op.add_column('service_checkins', sa.Column('order_id',     sa.Integer(),  sa.ForeignKey('orders.id', name='fk_checkin_order'), nullable=True))
    op.add_column('service_checkins', sa.Column('type',         sa.String(10), nullable=False, server_default='checkin'))

    # Renomeia executed_at para manter compatibilidade
    # executed_at continua existindo como timestamp geral
    op.create_index('ix_checkins_order', 'service_checkins', ['order_id'])


def downgrade():
    op.drop_index('ix_checkins_order', table_name='service_checkins')
    op.drop_column('service_checkins', 'type')
    op.drop_column('service_checkins', 'order_id')
    op.drop_column('service_checkins', 'duration_min')
    op.drop_column('service_checkins', 'checkout_at')
    op.drop_column('service_checkins', 'checkin_at')