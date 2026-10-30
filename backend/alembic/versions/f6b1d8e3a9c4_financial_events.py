"""journal des décisions : table financial_events

Revision ID: f6b1d8e3a9c4
Revises: e5a0c3d7f2b8
Create Date: 2026-10-26 17:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f6b1d8e3a9c4"
down_revision: Union[str, Sequence[str], None] = "e5a0c3d7f2b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("financial_events"):  # base créée par create_all
        return
    op.create_table(
        "financial_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_financial_events_id"), "financial_events", ["id"], unique=False)
    op.create_index(op.f("ix_financial_events_date"), "financial_events", ["date"], unique=False)
    op.create_index(op.f("ix_financial_events_account_id"), "financial_events", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_financial_events_account_id"), table_name="financial_events")
    op.drop_index(op.f("ix_financial_events_date"), table_name="financial_events")
    op.drop_index(op.f("ix_financial_events_id"), table_name="financial_events")
    op.drop_table("financial_events")
