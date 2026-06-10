"""add currency and original_amount to transactions

Revision ID: 8acb7caca7fd
Revises: 88272dbc341e
Create Date: 2026-05-19 19:43:20.586984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8acb7caca7fd'
down_revision: Union[str, Sequence[str], None] = '88272dbc341e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Transactions
    op.add_column('transactions', sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'))
    op.add_column('transactions', sa.Column('original_amount', sa.Float(), nullable=True))
    op.execute("UPDATE transactions SET original_amount = amount")
    
    # Investment Transactions
    op.add_column('investment_transactions', sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'))
    op.add_column('investment_transactions', sa.Column('original_amount', sa.Float(), nullable=True))
    op.execute("UPDATE investment_transactions SET original_amount = amount")


def downgrade() -> None:
    op.drop_column('investment_transactions', 'original_amount')
    op.drop_column('investment_transactions', 'currency')
    op.drop_column('transactions', 'original_amount')
    op.drop_column('transactions', 'currency')
