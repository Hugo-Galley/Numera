"""journal des connexions : table login_events

Revision ID: c4e7a2d9f1b8
Revises: b8d3f1a6c2e4
Create Date: 2026-10-27 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c4e7a2d9f1b8"
down_revision: Union[str, Sequence[str], None] = "b8d3f1a6c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("login_events"):  # base créée par create_all
        return
    op.create_table(
        "login_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_login_events_id"), "login_events", ["id"], unique=False)
    op.create_index(op.f("ix_login_events_created_at"), "login_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_login_events_created_at"), table_name="login_events")
    op.drop_index(op.f("ix_login_events_id"), table_name="login_events")
    op.drop_table("login_events")
