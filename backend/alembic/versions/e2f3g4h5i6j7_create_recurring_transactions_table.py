"""create_recurring_transactions_table

Revision ID: e2f3g4h5i6j7
Revises: 0143092e142d
Create Date: 2026-06-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, Sequence[str], None] = '0143092e142d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table exists (for users who already have it but missing migration)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'recurring_transactions' not in tables:
        op.create_table(
            'recurring_transactions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('account_id', sa.Integer(), nullable=False),
            sa.Column('merchant', sa.String(length=120), nullable=False),
            sa.Column('amount', sa.Float(), nullable=False),
            sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
            sa.Column('category_id', sa.Integer(), nullable=True),
            sa.Column('frequency', sa.String(length=32), nullable=False),
            sa.Column('day_of_week', sa.Integer(), nullable=True),
            sa.Column('day_of_month', sa.Integer(), nullable=True),
            sa.Column('start_date', sa.DateTime(), nullable=False),
            sa.Column('end_date', sa.DateTime(), nullable=True),
            sa.Column('note', sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], name=op.f('fk_recurring_transactions_account_id_accounts')),
            sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_recurring_transactions_category_id_categories')),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_recurring_transactions'))
        )
        with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_recurring_transactions_account_id'), ['account_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_recurring_transactions_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_recurring_transactions_merchant'), ['merchant'], unique=False)


def downgrade() -> None:
    op.drop_table('recurring_transactions')
