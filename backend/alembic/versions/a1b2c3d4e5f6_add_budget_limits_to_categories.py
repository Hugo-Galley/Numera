"""add_budget_limits_to_categories

Revision ID: a1b2c3d4e5f6
Revises: 0138996e0f8b
Create Date: 2026-05-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0138996e0f8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('monthly_limit', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('annual_limit', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_column('annual_limit')
        batch_op.drop_column('monthly_limit')
