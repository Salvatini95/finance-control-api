"""pwa offline sync + pin temporario + role encarregado

Revision ID: f1a2b3c4d5e6
Revises: d3e4f5a6b7c8
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision      = 'f1a2b3c4d5e6'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on    = None


def upgrade():
    # ── ServiceCheckin: idempotência offline ──────────────────────────────────
    op.add_column('service_checkins',
        sa.Column('local_id', sa.String(40), nullable=True))
    op.add_column('service_checkins',
        sa.Column('synced_offline', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_checkin_local_id', 'service_checkins', ['local_id'], unique=False)

    # ── Tabela de PINs temporários ────────────────────────────────────────────
    op.create_table('checkin_pins',
        sa.Column('id',          sa.Integer(), primary_key=True),
        sa.Column('pin',         sa.String(6),  nullable=False),
        sa.Column('client_id',   sa.Integer(),  nullable=False),
        sa.Column('company_id',  sa.Integer(),  nullable=False),
        sa.Column('created_by',  sa.Integer(),  nullable=False),
        sa.Column('used_by',     sa.Integer(),  nullable=True),
        sa.Column('created_at',  sa.String(20), nullable=False, server_default='2026-01-01T00:00:00'),
        sa.Column('expires_at',  sa.String(20), nullable=False, server_default='2026-01-01T00:00:00'),
        sa.Column('used_at',     sa.String(20), nullable=True),
        sa.Column('status',      sa.String(20), nullable=False, server_default='ativo'),
        sa.ForeignKeyConstraint(['client_id'],  ['clients.id'],   name='fk_pin_client'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name='fk_pin_company'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'],     name='fk_pin_creator'),
    )
    op.create_index('ix_pin_company', 'checkin_pins', ['company_id'])
    op.create_index('ix_pin_client',  'checkin_pins', ['client_id'])
    op.create_index('ix_pin_status',  'checkin_pins', ['status'])

    # NOTA: role 'encarregado' não precisa migration — User.role é String.


def downgrade():
    op.drop_index('ix_pin_status',  table_name='checkin_pins')
    op.drop_index('ix_pin_client',  table_name='checkin_pins')
    op.drop_index('ix_pin_company', table_name='checkin_pins')
    op.drop_table('checkin_pins')
    op.drop_index('ix_checkin_local_id', table_name='service_checkins')
    op.drop_column('service_checkins', 'synced_offline')
    op.drop_column('service_checkins', 'local_id')