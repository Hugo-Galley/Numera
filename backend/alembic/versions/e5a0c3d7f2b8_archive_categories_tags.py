"""archivage : colonnes categories.archived et tags.archived

Revision ID: e5a0c3d7f2b8
Revises: d4f9b2c6e1a7
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e5a0c3d7f2b8"
down_revision: Union[str, Sequence[str], None] = "d4f9b2c6e1a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("categories", "tags"):
        if "archived" in {c["name"] for c in inspector.get_columns(table)}:  # base créée par create_all
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    for table in ("categories", "tags"):
        with op.batch_alter_table(table) as batch:
            batch.drop_column("archived")
