"""découpage d'une dépense entre plusieurs catégories : table transaction_splits

Revision ID: c3e8a1f5d9b2
Revises: b7d4f2a8c1e5
Create Date: 2026-10-26 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e8a1f5d9b2"
down_revision: Union[str, Sequence[str], None] = "b7d4f2a8c1e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("transaction_splits"):  # base créée par create_all
        return
    op.create_table(
        "transaction_splits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transaction_splits_id"), "transaction_splits", ["id"], unique=False)
    op.create_index(op.f("ix_transaction_splits_transaction_id"), "transaction_splits", ["transaction_id"], unique=False)
    op.create_index(op.f("ix_transaction_splits_category_id"), "transaction_splits", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transaction_splits_category_id"), table_name="transaction_splits")
    op.drop_index(op.f("ix_transaction_splits_transaction_id"), table_name="transaction_splits")
    op.drop_index(op.f("ix_transaction_splits_id"), table_name="transaction_splits")
    op.drop_table("transaction_splits")
