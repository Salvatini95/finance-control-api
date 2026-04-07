"""add companies and roles multi-tenant

Revision ID: bed3b2c9bb31
Revises: e48b4c9b4488
Create Date: 2026-04-05 20:42:11.861799

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bed3b2c9bb31'
down_revision = 'e48b4c9b4488'
branch_labels = None
depends_on = None


def upgrade():
    # ── tabela companies ──
    op.create_table('companies',
        sa.Column('id',         sa.Integer(),      nullable=False),
        sa.Column('name',       sa.String(200),    nullable=False),
        sa.Column('cnpj',       sa.String(30),     nullable=True),
        sa.Column('address',    sa.String(300),    nullable=True),
        sa.Column('logo',       sa.Text(),         nullable=True),
        sa.Column('plan',       sa.String(20),     nullable=False, server_default='free'),
        sa.Column('created_at', sa.String(20),     nullable=True),
        sa.Column('active',     sa.Boolean(),      nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )

    # ── company_id nas tabelas (nullable=True — sem server_default necessário) ──
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_bill_company', 'companies', ['company_id'], ['id'])

    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_client_company', 'companies', ['company_id'], ['id'])

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_order_company', 'companies', ['company_id'], ['id'])
        batch_op.create_foreign_key('fk_order_transaction', 'transactions', ['transaction_id'], ['id'])

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_product_company', 'companies', ['company_id'], ['id'])

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_quote_company', 'companies', ['company_id'], ['id'])
        batch_op.create_foreign_key('fk_quote_client', 'clients', ['client_id'], ['id'])

    with op.batch_alter_table('service_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_svcrecord_company', 'companies', ['company_id'], ['id'])

    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_stock_company', 'companies', ['company_id'], ['id'])

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_transaction_company', 'companies', ['company_id'], ['id'])

    # ── users: active e role com server_default ──
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active',     sa.Boolean(),     nullable=False, server_default='true'))
        batch_op.add_column(sa.Column('company_id', sa.Integer(),     nullable=True))
        batch_op.add_column(sa.Column('role',       sa.String(20),    nullable=False, server_default='admin'))
        batch_op.create_foreign_key('fk_user_company', 'companies', ['company_id'], ['id'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_company', type_='foreignkey')
        batch_op.drop_column('role')
        batch_op.drop_column('company_id')
        batch_op.drop_column('active')

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transaction_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.drop_constraint('fk_stock_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('service_records', schema=None) as batch_op:
        batch_op.drop_constraint('fk_svcrecord_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('quotes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_quote_client', type_='foreignkey')
        batch_op.drop_constraint('fk_quote_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_constraint('fk_product_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_transaction', type_='foreignkey')
        batch_op.drop_constraint('fk_order_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_client_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bill_company', type_='foreignkey')
        batch_op.drop_column('company_id')

    op.drop_table('companies')