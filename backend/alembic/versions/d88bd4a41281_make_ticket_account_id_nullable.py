"""make_ticket_account_id_nullable

Revision ID: d88bd4a41281
Revises: 7c257ae426ca
Create Date: 2026-09-24 16:46:53.050015

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd88bd4a41281'
down_revision: Union[str, Sequence[str], None] = '7c257ae426ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('salary_configs', schema=None) as batch_op:
        batch_op.alter_column('ticket_account_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('salary_configs', schema=None) as batch_op:
        batch_op.alter_column('ticket_account_id',
               existing_type=sa.INTEGER(),
               nullable=False)
