"""add is_subscription_ignored to transactions

Revision ID: 3cd86e099271
Revises: 5f70692fbe6f
Create Date: 2026-06-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cd86e099271'
down_revision: Union[str, None] = '5f70692fbe6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('transactions', sa.Column('is_subscription_ignored', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('transactions', 'is_subscription_ignored')
