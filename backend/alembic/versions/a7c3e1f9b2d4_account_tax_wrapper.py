"""enveloppe fiscale et date d'ouverture d'un compte

Revision ID: a7c3e1f9b2d4
Revises: f1b7c4a9d2e6
Create Date: 2026-10-07 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e1f9b2d4"
down_revision: Union[str, None] = "f1b7c4a9d2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("tax_wrapper", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("opened_at", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("opened_at")
        batch.drop_column("tax_wrapper")
