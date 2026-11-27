"""référentiel des titres : table securities

Revision ID: b4d7f1a9c3e5
Revises: a8c3e5f1d7b2
Create Date: 2026-11-26 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4d7f1a9c3e5"
down_revision: str | Sequence[str] | None = "a8c3e5f1d7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("securities"):  # base créée par create_all
        return
    op.create_table(
        "securities",
        sa.Column("isin", sa.String(length=12), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country", sa.String(length=3), nullable=True),
        sa.Column("sector", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("isin"),
    )
    op.create_index(op.f("ix_securities_ticker"), "securities", ["ticker"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_securities_ticker"), table_name="securities")
    op.drop_table("securities")
