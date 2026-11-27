"""plus aucune composition d'ETF codée en dur : vide les champs de source `preset`

Revision ID: d8f3b6a1c9e4
Revises: c6e1a9d4f7b2
Create Date: 2026-11-27 12:00:00.000000

"""
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d8f3b6a1c9e4"
down_revision: str | Sequence[str] | None = "c6e1a9d4f7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPTY = {"countries": "{}", "sectors": "{}", "top_holdings": "[]"}


def _sources(raw: str | None) -> dict:
    try:
        sources = json.loads(raw or "{}")
    except ValueError:
        return {}
    return sources if isinstance(sources, dict) else {}


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, composition_sources FROM etf_profiles")).fetchall()
    for profile_id, raw in rows:
        sources = _sources(raw)
        preset = [field for field in _EMPTY if sources.get(field) == "preset"]
        if not preset:
            continue
        values = {field: _EMPTY[field] for field in preset}
        values["composition_sources"] = json.dumps({k: v for k, v in sources.items() if k not in preset})
        # Les colonnes viennent de la liste fixe `_EMPTY` ; `composition_refreshed_at` vidé : relu au prochain passage
        assignments = ", ".join(f"{column} = :{column}" for column in values)
        bind.execute(
            sa.text(f"UPDATE etf_profiles SET {assignments}, composition_refreshed_at = NULL WHERE id = :id"),
            {**values, "id": profile_id},
        )


def downgrade() -> None:
    """Sans effet : les compositions figées ne sont plus livrées avec l'application."""
