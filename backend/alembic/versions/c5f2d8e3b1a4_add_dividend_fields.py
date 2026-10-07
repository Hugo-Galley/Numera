"""dividendes : retenue à la source, réinvestissement, titre distribuant

Revision ID: c5f2d8e3b1a4
Revises: b4e1c7d2a9f3
Create Date: 2026-10-07 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5f2d8e3b1a4"
down_revision: Union[str, None] = "b4e1c7d2a9f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("investment_transactions") as batch:
        batch.add_column(sa.Column("withholding_tax", sa.Float(), nullable=True))
        batch.add_column(sa.Column("reinvested", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("reinvest_of_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_investment_transactions_reinvest_of_id",
            "investment_transactions",
            ["reinvest_of_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch.create_index("ix_investment_transactions_reinvest_of_id", ["reinvest_of_id"])
    with op.batch_alter_table("portfolio_holdings") as batch:
        batch.add_column(sa.Column("pays_dividends", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio_holdings") as batch:
        batch.drop_column("pays_dividends")
    with op.batch_alter_table("investment_transactions") as batch:
        batch.drop_index("ix_investment_transactions_reinvest_of_id")
        batch.drop_constraint("fk_investment_transactions_reinvest_of_id", type_="foreignkey")
        batch.drop_column("reinvest_of_id")
        batch.drop_column("reinvested")
        batch.drop_column("withholding_tax")
