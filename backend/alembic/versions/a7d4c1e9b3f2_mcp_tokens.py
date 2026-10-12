"""tokens d'accès MCP générés depuis l'interface

Revision ID: a7d4c1e9b3f2
Revises: f6b3d9e2a7c4
Create Date: 2026-10-12 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d4c1e9b3f2"
down_revision: Union[str, None] = "f6b3d9e2a7c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mcp_tokens_id"), "mcp_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_mcp_tokens_token_hash"), "mcp_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_mcp_tokens_token_hash"), table_name="mcp_tokens")
    op.drop_index(op.f("ix_mcp_tokens_id"), table_name="mcp_tokens")
    op.drop_table("mcp_tokens")
