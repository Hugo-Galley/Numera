"""règles de virement interne et origine des liens

Revision ID: b8d2f4a6c1e3
Revises: a7c3e1f9b2d4
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d2f4a6c1e3"
down_revision: Union[str, None] = "a7c3e1f9b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transfer_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dest_account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pattern", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("amount_tolerance_pct", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("day_tolerance", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_transfer_rules_id", "transfer_rules", ["id"])
    op.create_index("ix_transfer_rules_source_account_id", "transfer_rules", ["source_account_id"])
    op.create_index("ix_transfer_rules_dest_account_id", "transfer_rules", ["dest_account_id"])

    for table in ("transactions", "investment_transactions"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("link_origin", sa.String(length=16), nullable=True))
            batch.add_column(sa.Column("transfer_rule_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(f"fk_{table}_transfer_rule", "transfer_rules", ["transfer_rule_id"], ["id"], ondelete="SET NULL")
            batch.create_index(f"ix_{table}_transfer_rule_id", ["transfer_rule_id"])
        # Les liens existants ont été créés à la main
        op.execute(f"UPDATE {table} SET link_origin = 'manual' WHERE is_transfer = 1")

    with op.batch_alter_table("recurring_transactions") as batch:
        batch.add_column(sa.Column("transfer_to_account_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_recurring_transfer_to_account", "accounts", ["transfer_to_account_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("recurring_transactions") as batch:
        batch.drop_constraint("fk_recurring_transfer_to_account", type_="foreignkey")
        batch.drop_column("transfer_to_account_id")
    for table in ("investment_transactions", "transactions"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_transfer_rule_id")
            batch.drop_constraint(f"fk_{table}_transfer_rule", type_="foreignkey")
            batch.drop_column("transfer_rule_id")
            batch.drop_column("link_origin")
    op.drop_table("transfer_rules")
