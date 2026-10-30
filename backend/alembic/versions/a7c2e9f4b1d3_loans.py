"""crédits : tables loans et loan_prepayments

Revision ID: a7c2e9f4b1d3
Revises: f6b1d8e3a9c4
Create Date: 2026-10-26 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a7c2e9f4b1d3"
down_revision: Union[str, Sequence[str], None] = "f6b1d8e3a9c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("loans"):  # base créée par create_all
        return
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("principal", sa.Float(), nullable=False),
        sa.Column("annual_rate_pct", sa.Float(), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("insurance_monthly", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_loans_id"), "loans", ["id"], unique=False)
    op.create_index(op.f("ix_loans_account_id"), "loans", ["account_id"], unique=True)
    op.create_table(
        "loan_prepayments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_loan_prepayments_id"), "loan_prepayments", ["id"], unique=False)
    op.create_index(op.f("ix_loan_prepayments_loan_id"), "loan_prepayments", ["loan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_loan_prepayments_loan_id"), table_name="loan_prepayments")
    op.drop_index(op.f("ix_loan_prepayments_id"), table_name="loan_prepayments")
    op.drop_table("loan_prepayments")
    op.drop_index(op.f("ix_loans_account_id"), table_name="loans")
    op.drop_index(op.f("ix_loans_id"), table_name="loans")
    op.drop_table("loans")
