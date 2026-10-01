"""add_etf_profiles_and_portfolio_holdings

Revision ID: dc9a98b4a88f
Revises: 01eca035c2fb
Create Date: 2026-10-01 17:36:33.095753

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc9a98b4a88f'
down_revision: Union[str, Sequence[str], None] = '01eca035c2fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create etf_profiles table
    op.create_table(
        'etf_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=False),
        sa.Column('isin', sa.String(length=20), nullable=True),
        sa.Column('aliases', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('countries', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('sectors', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('top_holdings', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_etf_profiles'))
    )
    with op.batch_alter_table('etf_profiles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_etf_profiles_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_etf_profiles_isin'), ['isin'], unique=False)
        batch_op.create_index(batch_op.f('ix_etf_profiles_ticker'), ['ticker'], unique=False)

    # 2. Create portfolio_holdings table
    op.create_table(
        'portfolio_holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=False),
        sa.Column('isin', sa.String(length=20), nullable=True),
        sa.Column('asset_name', sa.String(length=120), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('buy_price_avg', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('etf_profile_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_portfolio_holdings_account_id_accounts'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['etf_profile_id'], ['etf_profiles.id'], name=op.f('fk_portfolio_holdings_etf_profile_id_etf_profiles'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_portfolio_holdings'))
    )
    with op.batch_alter_table('portfolio_holdings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_portfolio_holdings_account_id'), ['account_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_portfolio_holdings_etf_profile_id'), ['etf_profile_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_portfolio_holdings_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_portfolio_holdings_isin'), ['isin'], unique=False)
        batch_op.create_index(batch_op.f('ix_portfolio_holdings_ticker'), ['ticker'], unique=False)

    # 3. Migrate any existing test asset_holdings into portfolio_holdings
    try:
        conn = op.get_bind()
        tables = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        table_names = [t[0] for t in tables]
        if 'asset_holdings' in table_names and 'assets' in table_names:
            op.execute("""
                INSERT INTO portfolio_holdings (account_id, ticker, isin, asset_name, quantity, buy_price_avg, currency, created_at, updated_at)
                SELECT 
                    ah.account_id, 
                    a.symbol, 
                    NULL, 
                    a.name, 
                    ah.quantity, 
                    ah.average_purchase_price, 
                    COALESCE(a.currency, 'EUR'),
                    datetime('now'), 
                    datetime('now')
                FROM asset_holdings ah
                JOIN assets a ON ah.asset_id = a.id
            """)
            op.drop_table('asset_holdings')
            op.drop_table('assets')
    except Exception as e:
        print(f"Warning during legacy asset_holdings migration: {e}")

    # 4. Add columns to investment_transactions
    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ticker', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('isin', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('quantity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('unit_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('etf_profile_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_investment_transactions_etf_profile_id'), ['etf_profile_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_investment_transactions_isin'), ['isin'], unique=False)
        batch_op.create_index(batch_op.f('ix_investment_transactions_ticker'), ['ticker'], unique=False)
        batch_op.create_foreign_key(
            batch_op.f('fk_investment_transactions_etf_profile_id_etf_profiles'),
            'etf_profiles',
            ['etf_profile_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_investment_transactions_etf_profile_id_etf_profiles'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_investment_transactions_ticker'))
        batch_op.drop_index(batch_op.f('ix_investment_transactions_isin'))
        batch_op.drop_index(batch_op.f('ix_investment_transactions_etf_profile_id'))
        batch_op.drop_column('etf_profile_id')
        batch_op.drop_column('unit_price')
        batch_op.drop_column('quantity')
        batch_op.drop_column('isin')
        batch_op.drop_column('ticker')

    with op.batch_alter_table('portfolio_holdings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_portfolio_holdings_ticker'))
        batch_op.drop_index(batch_op.f('ix_portfolio_holdings_isin'))
        batch_op.drop_index(batch_op.f('ix_portfolio_holdings_id'))
        batch_op.drop_index(batch_op.f('ix_portfolio_holdings_etf_profile_id'))
        batch_op.drop_index(batch_op.f('ix_portfolio_holdings_account_id'))

    op.drop_table('portfolio_holdings')

    with op.batch_alter_table('etf_profiles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_etf_profiles_ticker'))
        batch_op.drop_index(batch_op.f('ix_etf_profiles_isin'))
        batch_op.drop_index(batch_op.f('ix_etf_profiles_id'))

    op.drop_table('etf_profiles')
