"""plus aucun profil ETF système : chaque position rejoint le profil de son propre fonds

Les règles sont celles de `app/domain/etf_attachment.py`, recopiées ici (une migration n'importe pas `app.*`).
Elles s'appliquent aussi aux opérations, à l'inventaire et aux récurrences qui désignent un profil système : le
rebuild recopie leur profil sur les positions.

Revision ID: e1b7c4a9f2d6
Revises: d8f3b6a1c9e4
Create Date: 2026-11-27 18:00:00.000000

"""
import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "e1b7c4a9f2d6"
down_revision: str | Sequence[str] | None = "d8f3b6a1c9e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables dont le profil est recopié sur les positions (noms fixes, jamais saisis)
_SOURCE_TABLES = ("holding_baseline_items", "investment_transactions", "recurring_transactions")


def _is_valid_isin(value: str) -> bool:
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value):
        return False
    digits = "".join(str(int(c, 36)) for c in value)
    total = 0
    for i, char in enumerate(reversed(digits)):
        n = int(char) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def _fund_isin(isin: str | None, ticker: str) -> str | None:
    """L'ISIN saisi, sinon celui contenu dans le symbole (`IE0002XZSHO1.SG`)."""
    for value in (isin or "", ticker.split(".")[0]):
        if _is_valid_isin(value.upper().strip()):
            return value.upper().strip()
    return None


def _aliases(raw: str | None) -> list[str] | None:
    try:
        values = json.loads(raw or "[]")
    except ValueError:
        return None
    return [str(v) for v in values] if isinstance(values, list) else None


def _clean(value: str | None) -> str:
    return (value or "").upper().strip()


def _is_named(profile: Any, ticker: str) -> bool:
    return _clean(ticker) in {_clean(n) for n in [profile.ticker, *(_aliases(profile.aliases) or [])]}


def _create_profile(bind: sa.Connection, name: str, ticker: str, isin: str) -> int:
    """Profil vide : sa composition sera lue au prochain passage."""
    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    bind.execute(sa.text(
        "INSERT INTO etf_profiles (name, ticker, isin, aliases, countries, sectors, top_holdings, composition_sources, "
        "is_system, created_at, updated_at) VALUES (:name, :ticker, :isin, :aliases, '{}', '{}', '[]', '{}', 0, "
        ":now, :now)"), {"name": name, "ticker": ticker, "isin": isin, "aliases": json.dumps([ticker, isin]), "now": now})
    return bind.execute(sa.text("SELECT max(id) FROM etf_profiles")).scalar_one()


def _attach_holdings(bind: sa.Connection, profiles: dict[int, Any], by_isin: dict[str, int]) -> None:
    rows = bind.execute(sa.text(
        "SELECT id, ticker, isin, asset_name, etf_profile_id FROM portfolio_holdings ORDER BY id")).fetchall()
    for row in rows:
        current = profiles.get(row.etf_profile_id)
        isin = _fund_isin(row.isin, row.ticker)
        if not isin:
            if not (current and current.is_system and not _is_named(current, row.ticker)):
                continue
            target = None
        elif current is None:
            if isin not in by_isin:
                continue  # une action en direct a aussi un ISIN : rien n'est créé
            target = by_isin[isin]
        elif _clean(current.isin) == isin:
            continue
        else:
            if isin not in by_isin:
                by_isin[isin] = _create_profile(bind, row.asset_name, row.ticker, isin)
            target = by_isin[isin]
        bind.execute(sa.text("UPDATE portfolio_holdings SET etf_profile_id = :p WHERE id = :i"),
                     {"p": target, "i": row.id})


def _clean_sources(bind: sa.Connection, profiles: dict[int, Any], by_isin: dict[str, int]) -> None:
    """Une ligne sans titre (ni ticker ni ISIN) garde son choix : il ne désigne aucune position."""
    for table in _SOURCE_TABLES:
        rows = bind.execute(sa.text(
            f"SELECT id, ticker, isin, etf_profile_id FROM {table} WHERE etf_profile_id IS NOT NULL")).fetchall()
        for row in rows:
            current = profiles.get(row.etf_profile_id)
            if not (current and current.is_system and row.ticker):
                continue
            isin = _fund_isin(row.isin, row.ticker)
            if isin == _clean(current.isin) or (not isin and _is_named(current, row.ticker)):
                continue
            bind.execute(sa.text(f"UPDATE {table} SET etf_profile_id = :p WHERE id = :i"),
                         {"p": by_isin.get(isin) if isin else None, "i": row.id})


def _used_tickers(bind: sa.Connection, profile_id: int) -> set[str] | None:
    """Tickers des lignes qui désignent encore ce profil ; None si plus rien ne le désigne."""
    tickers: set[str] = set()
    used = False
    for table in ("portfolio_holdings", *_SOURCE_TABLES):
        rows = bind.execute(sa.text(f"SELECT ticker FROM {table} WHERE etf_profile_id = :p"),
                            {"p": profile_id}).fetchall()
        used = used or bool(rows)
        tickers |= {_clean(r.ticker) for r in rows}
    reference = bind.execute(sa.text("SELECT 1 FROM etf_profiles WHERE exposure_profile_id = :p"),
                             {"p": profile_id}).first()
    return tickers if used or reference else None


def _retire_system_profiles(bind: sa.Connection, profiles: dict[int, Any]) -> None:
    """Supprime ceux que plus rien n'utilise ; les autres perdent le drapeau et les alias livrés qui ne servent pas."""
    for profile in (p for p in profiles.values() if p.is_system):
        used = _used_tickers(bind, profile.id)
        if used is None:
            bind.execute(sa.text("DELETE FROM etf_constituents WHERE profile_id = :p"), {"p": profile.id})
            bind.execute(sa.text("DELETE FROM etf_profiles WHERE id = :p"), {"p": profile.id})
            continue
        keep = used | {_clean(profile.ticker), _clean(profile.isin)}
        aliases = [a for a in _aliases(profile.aliases) or [] if _clean(a) in keep]
        bind.execute(sa.text("UPDATE etf_profiles SET is_system = 0, aliases = :a WHERE id = :p"),
                     {"a": json.dumps(aliases), "p": profile.id})


def upgrade() -> None:
    bind = op.get_bind()
    profiles = {p.id: p for p in bind.execute(sa.text(
        "SELECT id, ticker, isin, aliases, is_system FROM etf_profiles ORDER BY id")).fetchall()}
    by_isin: dict[str, int] = {}
    for profile in profiles.values():
        if profile.isin:
            by_isin.setdefault(_clean(profile.isin), profile.id)
    _attach_holdings(bind, profiles, by_isin)
    _clean_sources(bind, profiles, by_isin)
    _retire_system_profiles(bind, profiles)


def downgrade() -> None:
    """Sans effet : les profils livrés avec l'application ne reviennent pas."""
