"""Rattrapage : aligne un schéma migré sur les modèles (colonnes, index, unicité, ON DELETE).

Une base créée uniquement par les migrations s'écartait des modèles (audit R3) : colonnes de
`recurring_transactions` commentées dans une ancienne révision, index et contrainte d'unicité
absents, clés étrangères sans ON DELETE (donc suppression d'un compte ou d'une catégorie refusée
quand PRAGMA foreign_keys=ON). Chaque étape ne s'applique que si la base en a besoin : sur une
base créée par `create_all` (cas de la production), cette révision ne fait rien.

Revision ID: a9c1e4d7b2f6
Revises: e3c8a1f5b7d2
Create Date: 2026-10-24 20:00:00
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a9c1e4d7b2f6"
down_revision: Union[str, Sequence[str], None] = "e3c8a1f5b7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, colonne, table référencée, ON DELETE voulu) — identique aux modèles
FOREIGN_KEYS = [
    ("balance_snapshots", "account_id", "accounts", "CASCADE"),
    ("categorization_rules", "category_id", "categories", "SET NULL"),
    ("investment_transactions", "account_id", "accounts", "CASCADE"),
    ("merchant_aliases", "merchant_id", "merchants", "CASCADE"),
    ("merchants", "category_id", "categories", "SET NULL"),
    ("recurring_transactions", "account_id", "accounts", "CASCADE"),
    ("recurring_transactions", "category_id", "categories", "SET NULL"),
    ("salary_months", "salary_config_id", "salary_configs", "CASCADE"),
    ("savings_goals", "account_id", "accounts", "SET NULL"),
    ("savings_goals", "category_id", "categories", "SET NULL"),
    ("telecommuting_days", "salary_config_id", "salary_configs", "CASCADE"),
    ("transaction_tags", "tag_id", "tags", "CASCADE"),
    ("transaction_tags", "transaction_id", "transactions", "CASCADE"),
    ("transactions", "account_id", "accounts", "CASCADE"),
    ("transactions", "category_id", "categories", "SET NULL"),
]

# Une clé étrangère sans nom (base `create_all`) reçoit ce nom à la réflexion, ce qui permet de la remplacer.
NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def _fk_name(table: str, column: str, ref: str) -> str:
    return f"fk_{table}_{column}_{ref}"


def _wrong_foreign_keys(insp) -> dict[str, list[tuple[str, str, str, str | None]]]:
    """Clés étrangères dont le ON DELETE diffère des modèles, par table."""
    wrong: dict[str, list] = {}
    existing_tables = set(insp.get_table_names())
    for table, column, ref, ondelete in FOREIGN_KEYS:
        if table not in existing_tables:
            continue
        for fk in insp.get_foreign_keys(table):
            if fk["constrained_columns"] == [column] and fk["referred_table"] == ref:
                current = (fk.get("options") or {}).get("ondelete")
                if (current or "").upper() != ondelete:
                    wrong.setdefault(table, []).append((column, ref, ondelete, fk.get("name")))
    return wrong


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. Colonnes de génération des récurrences (ligne commentée dans la révision 158313575183)
    rec_columns = {c["name"] for c in insp.get_columns("recurring_transactions")}
    with op.batch_alter_table("recurring_transactions") as batch:
        if "last_generated_date" not in rec_columns:
            batch.add_column(sa.Column("last_generated_date", sa.DateTime(), nullable=True))
        if "auto_generate" not in rec_columns:
            batch.add_column(sa.Column("auto_generate", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    # 2. Index déclarés par les modèles
    insp = sa.inspect(bind)
    wanted_indexes = [
        ("ix_transactions_month_label", "transactions", ["month_label"]),
        ("ix_recurring_transactions_category_id", "recurring_transactions", ["category_id"]),
    ]
    for name, table, cols in wanted_indexes:
        if name not in {i["name"] for i in insp.get_indexes(table)}:
            op.create_index(name, table, cols)

    # 3. Unicité (compte de salaire, date) des jours de télétravail ; doublons éventuels retirés d'abord
    uniques = [tuple(u["column_names"]) for u in insp.get_unique_constraints("telecommuting_days")]
    unique_idx = [tuple(i["column_names"]) for i in insp.get_indexes("telecommuting_days") if i.get("unique")]
    needs_unique = ("salary_config_id", "date") not in uniques + unique_idx
    if needs_unique:
        op.execute(
            "DELETE FROM telecommuting_days WHERE id NOT IN "
            "(SELECT MIN(id) FROM telecommuting_days GROUP BY salary_config_id, date)"
        )

    # 4. ON DELETE : une seule reconstruction de table par table concernée
    wrong = _wrong_foreign_keys(insp)
    tables = set(wrong) | ({"telecommuting_days"} if needs_unique else set())
    for table in sorted(tables):
        with op.batch_alter_table(table, recreate="always", naming_convention=NAMING) as batch:
            for column, ref, ondelete, current_name in wrong.get(table, []):
                batch.drop_constraint(current_name or _fk_name(table, column, ref), type_="foreignkey")
                batch.create_foreign_key(
                    _fk_name(table, column, ref), ref, [column], ["id"], ondelete=ondelete
                )
            if table == "telecommuting_days" and needs_unique:
                batch.create_unique_constraint(
                    "uq_telecommuting_config_date", ["salary_config_id", "date"]
                )


def downgrade() -> None:
    # Rattrapage de schéma : rien à défaire (les contraintes voulues par les modèles restent valides).
    pass
