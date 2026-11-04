"""transactions : marchand et type bruts de l'import (clé de doublon)

Revision ID: a7c3e9d1b5f8
Revises: e3b7c1d9a4f2
Create Date: 2026-11-04 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7c3e9d1b5f8"
down_revision: str | None = "e3b7c1d9a4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("transactions")}
    with op.batch_alter_table("transactions") as batch:
        if "original_merchant" not in columns:  # base créée par create_all avec le modèle à jour
            batch.add_column(sa.Column("original_merchant", sa.String(120), nullable=True))
        if "original_type" not in columns:
            batch.add_column(sa.Column("original_type", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("original_type")
        batch.drop_column("original_merchant")
