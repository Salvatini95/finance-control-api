"""add clients orders stock service tables

Revision ID: ba2d07c3615d
Revises: bb53f290c54a
Create Date: 2026-03-31 07:41:11.009637

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba2d07c3615d'
down_revision = 'bb53f290c54a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('clients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('document', sa.String(length=50), nullable=True),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.String(length=20), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_client_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('origin', sa.String(length=20), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('payment_terms', sa.String(length=300), nullable=True),
    sa.Column('discount', sa.Float(), nullable=False),
    sa.Column('items_json', sa.Text(), nullable=False),
    sa.Column('subtotal', sa.Float(), nullable=False),
    sa.Column('total', sa.Float(), nullable=False),
    sa.Column('created_at', sa.String(length=20), nullable=True),
    sa.Column('finished_at', sa.String(length=20), nullable=True),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('quote_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='fk_order_client'),
    sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], name='fk_order_quote'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_order_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('service_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.String(length=20), nullable=True),
    sa.Column('duration_min', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='fk_svcrecord_client'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_svcrecord_order'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_svcrecord_product'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_svcrecord_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stock_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=10), nullable=False),
    sa.Column('qty', sa.Float(), nullable=False),
    sa.Column('cost', sa.Float(), nullable=True),
    sa.Column('reason', sa.String(length=200), nullable=True),
    sa.Column('date', sa.String(length=20), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_stock_order'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_stock_product'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_stock_user'),
    sa.PrimaryKeyConstraint('id')
    )

    # ── colunas novas em products com server_default para o SQLite aceitar ──
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stock_qty',      sa.Float(),   nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('stock_min',      sa.Float(),   nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('stock_avg_cost', sa.Float(),   nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('services_count', sa.Integer(), nullable=False, server_default='0'))

    # ── client_id em quotes (nullable=True, sem FK nomeada para evitar erro SQLite) ──
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_column('client_id')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('services_count')
        batch_op.drop_column('stock_avg_cost')
        batch_op.drop_column('stock_min')
        batch_op.drop_column('stock_qty')

    op.drop_table('stock_movements')
    op.drop_table('service_records')
    op.drop_table('orders')
    op.drop_table('clients')