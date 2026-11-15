"""Compte détenu pour un tiers : accounts.held_for

Revision ID: b7d2f4a91c35
Revises: d9a3b5e7c2f1
Create Date: 2026-11-15 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7d2f4a91c35'
down_revision: str | Sequence[str] | None = 'd9a3b5e7c2f1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "held_for" not in _columns("accounts"):  # base créée par create_all : colonne déjà là
        with op.batch_alter_table("accounts") as batch:
            batch.add_column(sa.Column("held_for", sa.String(length=60), nullable=True))


def downgrade() -> None:
    if "held_for" in _columns("accounts"):
        with op.batch_alter_table("accounts") as batch:
            batch.drop_column("held_for")
