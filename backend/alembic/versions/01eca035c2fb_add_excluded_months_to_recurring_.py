"""add_excluded_months_to_recurring_transactions

Revision ID: 01eca035c2fb
Revises: d88bd4a41281
Create Date: 2026-09-30 19:43:11.799499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01eca035c2fb'
down_revision: Union[str, Sequence[str], None] = 'd88bd4a41281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('excluded_months', sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('recurring_transactions', schema=None) as batch_op:
        batch_op.drop_column('excluded_months')
