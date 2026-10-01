"""add_securities_fields_to_recurring_transactions

Revision ID: 8cf9c97ea492
Revises: dc9a98b4a88f
Create Date: 2026-10-01 22:27:47.684375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cf9c97ea492'
down_revision: Union[str, Sequence[str], None] = 'dc9a98b4a88f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ticker', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('isin', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('quantity', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('unit_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('etf_profile_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_recurring_transactions_ticker'), ['ticker'], unique=False)
        batch_op.create_index(batch_op.f('ix_recurring_transactions_isin'), ['isin'], unique=False)
        batch_op.create_index(batch_op.f('ix_recurring_transactions_etf_profile_id'), ['etf_profile_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_recurring_transactions_etf_profile_id_etf_profiles'), 'etf_profiles', ['etf_profile_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_recurring_transactions_etf_profile_id_etf_profiles'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_recurring_transactions_etf_profile_id'))
        batch_op.drop_index(batch_op.f('ix_recurring_transactions_isin'))
        batch_op.drop_index(batch_op.f('ix_recurring_transactions_ticker'))
        batch_op.drop_column('etf_profile_id')
        batch_op.drop_column('unit_price')
        batch_op.drop_column('quantity')
        batch_op.drop_column('isin')
        batch_op.drop_column('ticker')
