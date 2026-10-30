"""achats programmés en parts entières : colonne recurring_transactions.whole_shares

Revision ID: b7d4f2a8c1e5
Revises: a9c1e4d7b2f6
Create Date: 2026-10-25 16:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b7d4f2a8c1e5"
down_revision: Union[str, Sequence[str], None] = "a9c1e4d7b2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("recurring_transactions")}
    if "whole_shares" in columns:  # base créée par create_all avec le modèle à jour
        return
    with op.batch_alter_table("recurring_transactions") as batch:
        batch.add_column(sa.Column("whole_shares", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("recurring_transactions") as batch:
        batch.drop_column("whole_shares")
