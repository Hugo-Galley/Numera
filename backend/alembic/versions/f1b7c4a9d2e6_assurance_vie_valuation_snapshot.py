"""assurance-vie : valorisation par relevés conservée pour les comptes existants

Revision ID: f1b7c4a9d2e6
Revises: d6a3e9f4c2b5
Create Date: 2026-10-07 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1b7c4a9d2e6"
down_revision: str | None = "d6a3e9f4c2b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Le mode « positions » devient possible pour l'assurance-vie ; les comptes existants restent aux relevés
    op.get_bind().execute(sa.text("UPDATE accounts SET valuation_mode = 'snapshot' WHERE type = 'assurance_vie'"))


def downgrade() -> None:
    pass
