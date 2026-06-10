"""add_recurring_and_custom_fields_to_transaction

Revision ID: 0138996e0f8b
Revises: 8acb7caca7fd
Create Date: 2026-05-20 08:58:58.382132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0138996e0f8b'
down_revision: Union[str, Sequence[str], None] = '8acb7caca7fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.alter_column('original_amount',
               existing_type=sa.FLOAT(),
               nullable=False)

    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('custom_icon', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('custom_color', sa.String(length=7), nullable=True))
        batch_op.alter_column('original_amount',
               existing_type=sa.FLOAT(),
               nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.alter_column('original_amount',
               existing_type=sa.FLOAT(),
               nullable=True)
        batch_op.drop_column('custom_color')
        batch_op.drop_column('custom_icon')
        batch_op.drop_column('is_recurring')

    with op.batch_alter_table('investment_transactions', schema=None) as batch_op:
        batch_op.alter_column('original_amount',
               existing_type=sa.FLOAT(),
               nullable=True)
