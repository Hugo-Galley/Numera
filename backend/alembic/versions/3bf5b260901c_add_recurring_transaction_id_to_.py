"""add recurring_transaction_id to investment_transactions

Revision ID: 3bf5b260901c
Revises: 86010323e83a
Create Date: 2026-06-08 22:33:28.946487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bf5b260901c'
down_revision: Union[str, Sequence[str], None] = '86010323e83a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('recurring_transaction_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_itx_recurring_tx', 'recurring_transactions', ['recurring_transaction_id'], ['id'])
        batch_op.create_index(batch_op.f('ix_investment_transactions_recurring_transaction_id'), ['recurring_transaction_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_investment_transactions_recurring_transaction_id'))
        batch_op.drop_constraint('fk_itx_recurring_tx', type_='foreignkey')
        batch_op.drop_column('recurring_transaction_id')
