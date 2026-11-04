"""historical_exchange_rates : un seul taux par (date, devise)

Revision ID: b7e2c4d9a1f3
Revises: a7d3f1c9e5b2
Create Date: 2026-11-04 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e2c4d9a1f3"
down_revision: str | Sequence[str] | None = "a7d3f1c9e5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "uq_historical_exchange_rates_date_currency"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if any(c["name"] == CONSTRAINT for c in inspector.get_unique_constraints("historical_exchange_rates")):
        return  # base créée par create_all
    # Doublons nés d'insertions concurrentes : on garde le plus ancien taux de chaque (date, devise)
    op.execute(
        "DELETE FROM historical_exchange_rates WHERE id NOT IN "
        "(SELECT MIN(id) FROM historical_exchange_rates GROUP BY date, currency)"
    )
    with op.batch_alter_table("historical_exchange_rates") as batch:
        batch.create_unique_constraint(CONSTRAINT, ["date", "currency"])


def downgrade() -> None:
    with op.batch_alter_table("historical_exchange_rates") as batch:
        batch.drop_constraint(CONSTRAINT, type_="unique")
