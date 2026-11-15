"""Achat décoté : investment_transactions.reference_price (cours de référence non décoté)

Revision ID: c4a8e1d6f2b9
Revises: b7d2f4a91c35
Create Date: 2026-11-15 23:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4a8e1d6f2b9'
down_revision: str | Sequence[str] | None = 'b7d2f4a91c35'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "reference_price" not in _columns("investment_transactions"):  # base créée par create_all : colonne déjà là
        with op.batch_alter_table("investment_transactions") as batch:
            batch.add_column(sa.Column("reference_price", sa.Float(), nullable=True))


def downgrade() -> None:
    if "reference_price" in _columns("investment_transactions"):
        with op.batch_alter_table("investment_transactions") as batch:
            batch.drop_column("reference_price")
