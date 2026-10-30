"""récurrences : jour d'arrivée différé d'un virement

Revision ID: d8f2a6c1e9b3
Revises: c5a9e1d7b2f4
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d8f2a6c1e9b3"
down_revision: Union[str, None] = "c5a9e1d7b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recurring_transactions", sa.Column("transfer_credit_day", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("transfer_credit_due", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("transfer_credit_due")
    with op.batch_alter_table("recurring_transactions") as batch:
        batch.drop_column("transfer_credit_day")
