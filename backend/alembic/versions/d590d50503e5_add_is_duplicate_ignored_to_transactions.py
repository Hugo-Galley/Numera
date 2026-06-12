"""add is_duplicate_ignored to transactions

Revision ID: d590d50503e5
Revises: d6e891ac64f5
Create Date: 2026-06-12 22:04:40.338901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd590d50503e5'
down_revision: Union[str, Sequence[str], None] = 'd6e891ac64f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column to transactions
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_duplicate_ignored', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove column from transactions
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('is_duplicate_ignored')
