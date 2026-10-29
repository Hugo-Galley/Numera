"""aides perçues (prime d'activité, APL…) : table benefits

Revision ID: e3b7c1d9a4f2
Revises: c4e7a2d9f1b8
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3b7c1d9a4f2"
down_revision: Union[str, Sequence[str], None] = "c4e7a2d9f1b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("benefits"):  # base créée par create_all
        return
    op.create_table(
        "benefits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("organization", sa.String(length=60), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_day", sa.Integer(), server_default="5", nullable=False),
        sa.Column("match_pattern", sa.String(length=120), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("declaration_interval_months", sa.Integer(), nullable=True),
        sa.Column("next_declaration_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benefits_id"), "benefits", ["id"], unique=False)
    op.create_index(op.f("ix_benefits_account_id"), "benefits", ["account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_benefits_account_id"), table_name="benefits")
    op.drop_index(op.f("ix_benefits_id"), table_name="benefits")
    op.drop_table("benefits")
