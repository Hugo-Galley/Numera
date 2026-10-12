"""Profils ETF : source et date de la composition (Yahoo / préréglage / saisie)

La composition des ETF vient désormais de Yahoo Finance. Les profils créés
auparavant par auto-décomposition recevaient une composition-type devinée à
partir du nom (archétypes « world », « tech »…) : on la reconnaît à sa
répartition par pays et on l'efface. Elle sera remplacée par les données
Yahoo à la prochaine actualisation.

Revision ID: f6b3d9e2a7c4
Revises: e5a1c7d3f9b2
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "f6b3d9e2a7c4"
down_revision = "e5a1c7d3f9b2"
branch_labels = None
depends_on = None

FIELDS = ("countries", "sectors", "top_holdings")

# Répartitions par pays des anciens archétypes (backend) et modèles (frontend)
ESTIMATED_COUNTRIES = [
    {"USA": 85.0, "TWN": 5.0, "NLD": 4.0, "KOR": 3.0, "Autres": 3.0},
    {"USA": 100.0},
    {"GBR": 22.0, "FRA": 18.0, "CHE": 15.0, "DEU": 13.0, "NLD": 7.5, "DNK": 5.0, "SWE": 4.5, "Autres": 15.0},
    {"CHN": 26.0, "IND": 21.0, "TWN": 18.0, "KOR": 11.0, "BRA": 5.5, "SAU": 4.0, "ZAF": 3.0, "Autres": 11.5},
    {"USA": 70.0, "CHE": 10.0, "DNK": 6.0, "GBR": 5.0, "FRA": 4.0, "Autres": 5.0},
    {"USA": 65.0, "JPN": 8.0, "GBR": 5.0, "AUS": 5.0, "FRA": 4.0, "SGP": 3.0, "Autres": 10.0},
    {"USA": 45.0, "FRA": 12.0, "DEU": 10.0, "JPN": 8.0, "ITA": 6.0, "GBR": 5.0, "Autres": 14.0},
    {"USA": 45.0, "FRA": 18.0, "DEU": 8.0, "GBR": 6.0, "JPN": 5.0, "CHE": 4.0, "Autres": 14.0},
    {"USA": 71.0, "JPN": 5.5, "GBR": 3.8, "CAN": 3.1, "FRA": 2.8, "CHE": 2.4, "DEU": 2.1, "Autres": 9.3},
    {"USA": 71.0, "JPN": 5.5, "GBR": 3.7, "FRA": 2.8, "DEU": 2.2, "Autres": 14.8},
    {"GBR": 22.0, "FRA": 18.0, "CHE": 14.0, "DEU": 13.5, "NLD": 7.0, "Autres": 25.5},
    {"CHN": 25.0, "IND": 20.0, "TWN": 19.0, "KOR": 11.0, "BRA": 5.0, "Autres": 20.0},
]


def _is_estimated(countries_json: str) -> bool:
    try:
        countries = json.loads(countries_json or "{}")
    except ValueError:
        return False
    return any(countries == estimate for estimate in ESTIMATED_COUNTRIES)


def upgrade() -> None:
    with op.batch_alter_table("etf_profiles") as batch_op:
        batch_op.add_column(sa.Column("composition_sources", sa.Text(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("composition_refreshed_at", sa.DateTime(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, is_system, countries, sectors, top_holdings FROM etf_profiles")).fetchall()
    for row in rows:
        if row.is_system:
            sources = {field: "preset" for field in FIELDS}
            conn.execute(
                sa.text("UPDATE etf_profiles SET composition_sources = :s WHERE id = :id"),
                {"s": json.dumps(sources), "id": row.id},
            )
        elif _is_estimated(row.countries):
            conn.execute(
                sa.text(
                    "UPDATE etf_profiles SET countries = '{}', sectors = '{}', top_holdings = '[]', "
                    "composition_sources = '{}' WHERE id = :id"
                ),
                {"id": row.id},
            )
        else:
            sources = {
                field: "manual"
                for field, value in zip(FIELDS, (row.countries, row.sectors, row.top_holdings))
                if value not in (None, "", "{}", "[]")
            }
            conn.execute(
                sa.text("UPDATE etf_profiles SET composition_sources = :s WHERE id = :id"),
                {"s": json.dumps(sources), "id": row.id},
            )


def downgrade() -> None:
    with op.batch_alter_table("etf_profiles") as batch_op:
        batch_op.drop_column("composition_refreshed_at")
        batch_op.drop_column("composition_sources")
