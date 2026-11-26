"""Nettoie les profils ETF parasites créés par la recherche (fonds à effet de levier, trusts crypto, CDR Cisco)

1. Retire des alias des profils non système les alias hérités de l'ancien code : le symbole tronqué avant le
   point (`CSCO` pour `CSCO.TO`) et le nom du fonds en majuscules.
2. Détache les positions dont ni le ticker ni l'ISIN ne correspondent exactement au profil (ticker ou alias).
3. Supprime les profils non système sans composition et sans aucune référence.

Revision ID: a8c3e5f1d7b2
Revises: 7d2e9b4c1a6f
Create Date: 2026-11-26 10:00:00

"""
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a8c3e5f1d7b2"
down_revision: str | Sequence[str] | None = "7d2e9b4c1a6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REFERENCING_TABLES = ("portfolio_holdings", "investment_transactions", "holding_baseline_items", "recurring_transactions")


def _load_aliases(raw: str | None) -> list:
    try:
        aliases = json.loads(raw or "[]")
    except ValueError:
        return []
    return aliases if isinstance(aliases, list) else []


def _clean_aliases(bind: sa.Connection) -> None:
    rows = bind.execute(sa.text("SELECT id, name, ticker, aliases FROM etf_profiles WHERE is_system = 0")).fetchall()
    for pid, name, ticker, raw in rows:
        aliases = _load_aliases(raw)
        junk = {str(name).upper()}
        if "." in ticker:
            junk.add(ticker.split(".")[0].upper())
        junk.discard(str(ticker).upper())
        kept = [a for a in aliases if str(a).upper() not in junk]
        if kept != aliases:
            bind.execute(sa.text("UPDATE etf_profiles SET aliases = :a WHERE id = :i"), {"a": json.dumps(kept), "i": pid})


def _detach_mismatched_holdings(bind: sa.Connection) -> None:
    profiles = {
        pid: ({str(ticker).upper(), *(str(a).upper().strip() for a in _load_aliases(raw))}, (isin or "").upper())
        for pid, ticker, raw, isin in bind.execute(sa.text("SELECT id, ticker, aliases, isin FROM etf_profiles"))
    }
    holdings = bind.execute(sa.text("SELECT id, ticker, isin, etf_profile_id FROM portfolio_holdings WHERE etf_profile_id IS NOT NULL")).fetchall()
    stale = []
    for hid, ticker, isin, pid in holdings:
        symbols, profile_isin = profiles.get(pid, (set(), ""))
        if str(ticker).upper().strip() not in symbols and not (isin and profile_isin and isin.upper() == profile_isin):
            stale.append(hid)
    if stale:
        bind.execute(sa.text("UPDATE portfolio_holdings SET etf_profile_id = NULL WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True)), {"ids": stale})


def _delete_empty_unreferenced(bind: sa.Connection) -> None:
    unreferenced = " AND ".join(
        f"id NOT IN (SELECT etf_profile_id FROM {table} WHERE etf_profile_id IS NOT NULL)" for table in REFERENCING_TABLES
    )
    bind.execute(
        sa.text(
            "DELETE FROM etf_profiles WHERE is_system = 0 AND countries IN ('{}', '') AND sectors IN ('{}', '') "
            f"AND top_holdings IN ('[]', '') AND {unreferenced}"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    _clean_aliases(bind)
    _detach_mismatched_holdings(bind)
    _delete_empty_unreferenced(bind)


def downgrade() -> None:
    """Sans effet : les profils supprimés et les rattachements retirés étaient parasites (données non restaurables)."""
