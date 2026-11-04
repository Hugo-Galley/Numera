"""investment_transactions.unit_price_derived : origine du prix unitaire (saisi ou déduit du montant)

Revision ID: a7d3f1c9e5b2
Revises: e3b7c1d9a4f2
Create Date: 2026-11-04 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7d3f1c9e5b2"
down_revision: str | Sequence[str] | None = "e3b7c1d9a4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("investment_transactions")}
    if "unit_price_derived" in columns:  # base créée par create_all
        return
    # Les lignes existantes valent « saisi » (0) : leur prix n'est jamais recalculé, comme avant
    op.add_column(
        "investment_transactions",
        sa.Column("unit_price_derived", sa.Boolean(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    with op.batch_alter_table("investment_transactions") as batch_op:
        batch_op.drop_column("unit_price_derived")
