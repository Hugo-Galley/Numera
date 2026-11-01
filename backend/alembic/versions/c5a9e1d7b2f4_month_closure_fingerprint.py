"""revue de fin de mois : empreinte des totaux par devise

Revision ID: c5a9e1d7b2f4
Revises: b3e8d2c5a1f7
Create Date: 2026-10-13 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5a9e1d7b2f4"
down_revision: str | None = "b3e8d2c5a1f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("month_closures", sa.Column("fingerprint", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("month_closures") as batch:
        batch.drop_column("fingerprint")
