"""notifications push : table notification_log

Revision ID: b8d3f1a6c2e4
Revises: a7c2e9f4b1d3
Create Date: 2026-10-26 23:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b8d3f1a6c2e4"
down_revision: Union[str, Sequence[str], None] = "a7c2e9f4b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("notification_log"):  # base créée par create_all
        return
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("action_id", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_log_id"), "notification_log", ["id"], unique=False)
    op.create_index(op.f("ix_notification_log_fingerprint"), "notification_log", ["fingerprint"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_log_fingerprint"), table_name="notification_log")
    op.drop_index(op.f("ix_notification_log_id"), table_name="notification_log")
    op.drop_table("notification_log")
