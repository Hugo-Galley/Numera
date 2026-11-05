"""holding_baseline_items.cost_basis_eur : coût de revient EUR saisi d'une ligne d'inventaire

Revision ID: c8f4a2d6b1e9
Revises: b7e2c4d9a1f3
Create Date: 2026-11-05 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8f4a2d6b1e9"
down_revision: str | Sequence[str] | None = "b7e2c4d9a1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("holding_baseline_items")}


def upgrade() -> None:
    if "cost_basis_eur" not in _columns():  # base créée par create_all
        op.add_column("holding_baseline_items", sa.Column("cost_basis_eur", sa.Float(), nullable=True))


def downgrade() -> None:
    if "cost_basis_eur" in _columns():
        with op.batch_alter_table("holding_baseline_items") as batch:
            batch.drop_column("cost_basis_eur")
