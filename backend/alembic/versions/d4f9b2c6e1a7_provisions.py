"""provisions pour grosses dépenses périodiques : table provisions

Revision ID: d4f9b2c6e1a7
Revises: c3e8a1f5d9b2
Create Date: 2026-10-26 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4f9b2c6e1a7"
down_revision: Union[str, Sequence[str], None] = "c3e8a1f5d9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("provisions"):  # base créée par create_all
        return
    op.create_table(
        "provisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("interval_months", sa.Integer(), server_default="12", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provisions_id"), "provisions", ["id"], unique=False)
    op.create_index(op.f("ix_provisions_category_id"), "provisions", ["category_id"], unique=False)
    op.create_index(op.f("ix_provisions_account_id"), "provisions", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_provisions_account_id"), table_name="provisions")
    op.drop_index(op.f("ix_provisions_category_id"), table_name="provisions")
    op.drop_index(op.f("ix_provisions_id"), table_name="provisions")
    op.drop_table("provisions")
