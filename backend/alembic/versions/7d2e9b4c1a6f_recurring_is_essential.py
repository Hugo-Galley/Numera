"""recurring_transactions.is_essential : charge essentielle ou non (NULL = déduit de la catégorie)

Revision ID: 7d2e9b4c1a6f
Revises: 3e1fd3f89624
Create Date: 2026-11-16 10:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7d2e9b4c1a6f"
down_revision: str | Sequence[str] | None = "3e1fd3f89624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "is_essential" not in _columns("recurring_transactions"):  # base créée par create_all : colonne déjà là
        with op.batch_alter_table("recurring_transactions") as batch:
            batch.add_column(sa.Column("is_essential", sa.Boolean(), nullable=True))


def downgrade() -> None:
    if "is_essential" in _columns("recurring_transactions"):
        with op.batch_alter_table("recurring_transactions") as batch:
            batch.drop_column("is_essential")
