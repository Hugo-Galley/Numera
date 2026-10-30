"""revue de fin de mois : table month_closures et colonne transactions.is_exceptional

Revision ID: b3e8d2c5a1f7
Revises: a7d4c1e9b3f2
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b3e8d2c5a1f7"
down_revision: Union[str, None] = "a7d4c1e9b3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "month_closures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=False),
        sa.Column("highlight", sa.String(length=500), nullable=True),
        sa.Column("tx_count", sa.Integer(), nullable=False),
        sa.Column("income", sa.Float(), nullable=False),
        sa.Column("expenses", sa.Float(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "month", name="uq_month_closures_year_month"),
    )
    op.create_index(op.f("ix_month_closures_id"), "month_closures", ["id"], unique=False)
    op.add_column(
        "transactions",
        sa.Column("is_exceptional", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("is_exceptional")
    op.drop_index(op.f("ix_month_closures_id"), table_name="month_closures")
    op.drop_table("month_closures")
