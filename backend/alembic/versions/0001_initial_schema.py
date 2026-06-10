"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-05-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_accounts_id", "accounts", ["id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_categories_id", "categories", ["id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("month_label", sa.String(length=20), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("merchant", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("running_balance", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_transactions_id", "transactions", ["id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_merchant", "transactions", ["merchant"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])

    op.create_table(
        "investment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_investment_transactions_id", "investment_transactions", ["id"])
    op.create_index("ix_investment_transactions_account_id", "investment_transactions", ["account_id"])
    op.create_index("ix_investment_transactions_date", "investment_transactions", ["date"])

    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("is_zero_point", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_balance_snapshots_id", "balance_snapshots", ["id"])
    op.create_index("ix_balance_snapshots_account_id", "balance_snapshots", ["account_id"])
    op.create_index("ix_balance_snapshots_date", "balance_snapshots", ["date"])

    op.create_table(
        "imports_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_imports_log_id", "imports_log", ["id"])


def downgrade() -> None:
    op.drop_index("ix_imports_log_id", table_name="imports_log")
    op.drop_table("imports_log")

    op.drop_index("ix_balance_snapshots_date", table_name="balance_snapshots")
    op.drop_index("ix_balance_snapshots_account_id", table_name="balance_snapshots")
    op.drop_index("ix_balance_snapshots_id", table_name="balance_snapshots")
    op.drop_table("balance_snapshots")

    op.drop_index("ix_investment_transactions_date", table_name="investment_transactions")
    op.drop_index("ix_investment_transactions_account_id", table_name="investment_transactions")
    op.drop_index("ix_investment_transactions_id", table_name="investment_transactions")
    op.drop_table("investment_transactions")

    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_index("ix_transactions_merchant", table_name="transactions")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_index("ix_transactions_id", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")

    op.drop_index("ix_accounts_id", table_name="accounts")
    op.drop_table("accounts")
