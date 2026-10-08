"""logo des récurrences

Revision ID: c3e9a1d7f5b2
Revises: b8d2f4a6c1e3
"""
from alembic import op
import sqlalchemy as sa

revision = "c3e9a1d7f5b2"
down_revision = "b8d2f4a6c1e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("recurring_transactions") as batch_op:
        batch_op.add_column(sa.Column("logo", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("recurring_transactions") as batch_op:
        batch_op.drop_column("logo")
