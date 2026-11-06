"""benefits.logo/auto_generate et transactions.benefit_id/is_provisional : entrées d'aides générées

Revision ID: d9a3b5e7c2f1
Revises: c8f4a2d6b1e9
Create Date: 2026-11-06 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9a3b5e7c2f1"
down_revision: str | Sequence[str] | None = "c8f4a2d6b1e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "logo" not in _columns("benefits"):  # base créée par create_all : colonnes déjà là
        with op.batch_alter_table("benefits") as batch:
            batch.add_column(sa.Column("logo", sa.String(length=64), nullable=True))
            batch.add_column(sa.Column("auto_generate", sa.Boolean(), nullable=False, server_default="0"))
    if "benefit_id" not in _columns("transactions"):
        with op.batch_alter_table("transactions") as batch:
            batch.add_column(sa.Column("benefit_id", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("is_provisional", sa.Boolean(), nullable=False, server_default="0"))
            batch.create_foreign_key("fk_transactions_benefit_id", "benefits", ["benefit_id"], ["id"], ondelete="SET NULL")
            batch.create_index("ix_transactions_benefit_id", ["benefit_id"])


def downgrade() -> None:
    if "benefit_id" in _columns("transactions"):
        with op.batch_alter_table("transactions") as batch:
            batch.drop_index("ix_transactions_benefit_id")
            batch.drop_constraint("fk_transactions_benefit_id", type_="foreignkey")
            batch.drop_column("is_provisional")
            batch.drop_column("benefit_id")
    if "logo" in _columns("benefits"):
        with op.batch_alter_table("benefits") as batch:
            batch.drop_column("auto_generate")
            batch.drop_column("logo")
