"""investment_transactions.kept_as_cash : versement automatique laissé en espèces (plus proposé à relier)

Revision ID: 3e1fd3f89624
Revises: d9a3b5e7c2f1
Create Date: 2026-11-15 21:39:39.024908

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3e1fd3f89624"
down_revision: str | Sequence[str] | None = "d9a3b5e7c2f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "kept_as_cash" not in _columns("investment_transactions"):  # base créée par create_all : colonne déjà là
        with op.batch_alter_table("investment_transactions") as batch:
            batch.add_column(sa.Column("kept_as_cash", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    if "kept_as_cash" in _columns("investment_transactions"):
        with op.batch_alter_table("investment_transactions") as batch:
            batch.drop_column("kept_as_cash")
