"""comptes : logo de la banque

Revision ID: e3c8a1f5b7d2
Revises: d8f2a6c1e9b3
Create Date: 2026-10-24 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e3c8a1f5b7d2"
down_revision: Union[str, None] = "d8f2a6c1e9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("logo", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("logo")
