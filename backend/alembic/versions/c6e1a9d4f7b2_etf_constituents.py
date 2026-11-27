"""composition complète des ETF : lignes et origine de la composition

Revision ID: c6e1a9d4f7b2
Revises: b4d7f1a9c3e5
Create Date: 2026-11-27 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6e1a9d4f7b2"
down_revision: str | Sequence[str] | None = "b4d7f1a9c3e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("provider", "provider_ref", "replication", "index_name", "exposure_profile_id",
            "composition_as_of", "coverage_pct", "lines_count")


def _add_profile_columns() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("etf_profiles")}
    if "exposure_profile_id" in existing:  # base créée par create_all
        return
    # La table est recréée (clé étrangère au niveau de la table). La connexion d'Alembic n'active pas
    # `PRAGMA foreign_keys` : les positions rattachées aux profils ne sont pas détachées.
    with op.batch_alter_table("etf_profiles") as batch:
        batch.add_column(sa.Column("provider", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("provider_ref", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("replication", sa.String(length=16), nullable=False, server_default="unknown"))
        batch.add_column(sa.Column("index_name", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("exposure_profile_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("composition_as_of", sa.Date(), nullable=True))
        batch.add_column(sa.Column("coverage_pct", sa.Float(), nullable=True))
        batch.add_column(sa.Column("lines_count", sa.Integer(), nullable=False, server_default="0"))
        batch.create_foreign_key("fk_etf_profiles_exposure_profile_id_etf_profiles", "etf_profiles",
                                 ["exposure_profile_id"], ["id"], ondelete="SET NULL")


def upgrade() -> None:
    _add_profile_columns()
    if sa.inspect(op.get_bind()).has_table("etf_constituents"):  # base créée par create_all
        return
    op.create_table(
        "etf_constituents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("country", sa.String(length=3), nullable=True),
        sa.Column("sector", sa.String(length=64), nullable=False),
        sa.Column("asset_class", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["etf_profiles.id"], ondelete="CASCADE",
                                name="fk_etf_constituents_profile_id_etf_profiles"),
        sa.PrimaryKeyConstraint("id", name="pk_etf_constituents"),
    )
    op.create_index("ix_etf_constituents_profile_id", "etf_constituents", ["profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_etf_constituents_profile_id", table_name="etf_constituents")
    op.drop_table("etf_constituents")
    # Connexion Alembic sans `PRAGMA foreign_keys` : recréer la table ne détache aucune position
    with op.batch_alter_table("etf_profiles") as batch:
        for name in _COLUMNS:
            batch.drop_column(name)
