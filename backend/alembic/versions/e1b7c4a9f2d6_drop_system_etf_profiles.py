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


def _clean(value: str | None) -> str:
    return (value or "").upper().strip()


def _leaves(profile: Any, isin: str) -> bool:
    """Un profil saisi sans ISIN (non système) est un rattachement manuel : la position n'en part pas."""
    own = _clean(profile.isin)
    return own != isin and (bool(profile.is_system) or bool(own))


def plan_attachments(holdings: Sequence[Any], profiles: Sequence[Any]
                     ) -> tuple[dict[int, int], set[str], dict[int, str], set[int]]:
    """Copie de `domain/etf_attachment.py::plan_attachments` : (déplacements, ISIN à créer, en attente, détachées).

    Sans ISIN, une position ne reste sur un profil système que si son ticker est le ticker propre du profil : les
    alias livrés mélangeaient plusieurs fonds et ne valent plus rien."""
    by_id = {p.id: p for p in profiles}
    by_isin: dict[str, int] = {}
    for profile in sorted(profiles, key=lambda p: p.id):
        if profile.isin:
            by_isin.setdefault(_clean(profile.isin), profile.id)
    moves: dict[int, int] = {}
    create: set[str] = set()
    pending: dict[int, str] = {}
    detach: set[int] = set()
    unattached: dict[int, str] = {}
    for holding in holdings:
        current = by_id.get(holding.etf_profile_id or 0)
        isin = _fund_isin(holding.isin, holding.ticker)
        if not isin:
            if current and current.is_system and _clean(holding.ticker) != _clean(current.ticker):
                detach.add(holding.id)
        elif current is None:
            if isin in by_isin:
                moves[holding.id] = by_isin[isin]
            else:
                unattached[holding.id] = isin
        elif _leaves(current, isin):
            if isin in by_isin:
                moves[holding.id] = by_isin[isin]
            else:
                create.add(isin)
                pending[holding.id] = isin
    pending.update({hid: isin for hid, isin in unattached.items() if isin in create})
    return moves, create, pending, detach


def _create_profile(bind: sa.Connection, name: str, ticker: str, isin: str) -> int:
    """Profil vide : sa composition sera lue au prochain passage. Quelques-uns au plus, un par fonds."""
    now = datetime.now(UTC).replace(tzinfo=None).isoformat(sep=" ")
    result = bind.execute(sa.text(
        "INSERT INTO etf_profiles (name, ticker, isin, aliases, countries, sectors, top_holdings, composition_sources, "
        "is_system, created_at, updated_at) VALUES (:name, :ticker, :isin, :aliases, '{}', '{}', '[]', '{}', 0, "
        ":now, :now)"), {"name": name, "ticker": ticker, "isin": isin, "aliases": json.dumps([ticker, isin]), "now": now})
    return int(result.lastrowid)


def _set_profiles(bind: sa.Connection, table: str, targets: dict[int, int | None]) -> None:
    if targets:
        bind.execute(sa.text(f"UPDATE {table} SET etf_profile_id = :p WHERE id = :i"),
                     [{"p": p, "i": i} for i, p in targets.items()])


def _attach_holdings(bind: sa.Connection, profiles: dict[int, Any], by_isin: dict[str, int]) -> None:
    rows = bind.execute(sa.text(
        "SELECT id, ticker, isin, asset_name, etf_profile_id FROM portfolio_holdings ORDER BY id")).fetchall()
    moves, _, pending, detach = plan_attachments(rows, list(profiles.values()))
    targets: dict[int, int | None] = {**moves, **dict.fromkeys(detach)}
    for row in rows:  # la première position de chaque ISIN donne son nom et son ticker au profil créé
        isin = pending.get(row.id)
        if isin:
            if isin not in by_isin:
                by_isin[isin] = _create_profile(bind, row.asset_name, row.ticker, isin)
            targets[row.id] = by_isin[isin]
    _set_profiles(bind, "portfolio_holdings", targets)


def _clean_sources(bind: sa.Connection, profiles: dict[int, Any], by_isin: dict[str, int]) -> None:
    """Une ligne sans titre (ni ticker ni ISIN) garde son choix : il ne désigne aucune position."""
    for table in _SOURCE_TABLES:
        rows = bind.execute(sa.text(
            f"SELECT id, ticker, isin, etf_profile_id FROM {table} WHERE etf_profile_id IS NOT NULL")).fetchall()
        targets: dict[int, int | None] = {}
        for row in rows:
            current = profiles.get(row.etf_profile_id)
            if not (current and current.is_system and row.ticker):
                continue
            isin = _fund_isin(row.isin, row.ticker)
            if isin == _clean(current.isin) or (not isin and _clean(row.ticker) == _clean(current.ticker)):
                continue
            targets[row.id] = by_isin.get(isin) if isin else None
        _set_profiles(bind, table, targets)


def _used_profiles(bind: sa.Connection) -> set[int]:
    """Profils encore désignés par une ligne ou par une référence d'indice."""
    used: set[int] = set()
    for table in ("portfolio_holdings", *_SOURCE_TABLES):
        used |= {r[0] for r in bind.execute(sa.text(
            f"SELECT DISTINCT etf_profile_id FROM {table} WHERE etf_profile_id IS NOT NULL"))}
    used |= {r[0] for r in bind.execute(sa.text(
        "SELECT DISTINCT exposure_profile_id FROM etf_profiles WHERE exposure_profile_id IS NOT NULL"))}
    return used


def _retire_system_profiles(bind: sa.Connection, profiles: dict[int, Any]) -> None:
    """Supprime ceux que plus rien n'utilise ; les autres perdent le drapeau et tous leurs alias livrés."""
    used = _used_profiles(bind)
    system = [p for p in profiles.values() if p.is_system]
    gone = [{"p": p.id} for p in system if p.id not in used]
    if gone:
        bind.execute(sa.text("DELETE FROM etf_constituents WHERE profile_id = :p"), gone)
        bind.execute(sa.text("DELETE FROM etf_profiles WHERE id = :p"), gone)
    kept = [{"p": p.id, "a": json.dumps([n for n in (p.ticker, _clean(p.isin)) if n])}
            for p in system if p.id in used]
    if kept:
        bind.execute(sa.text("UPDATE etf_profiles SET is_system = 0, aliases = :a WHERE id = :p"), kept)


def upgrade() -> None:
    bind = op.get_bind()
    profiles = {p.id: p for p in bind.execute(sa.text(
        "SELECT id, ticker, isin, is_system FROM etf_profiles ORDER BY id")).fetchall()}
    by_isin: dict[str, int] = {}
    for profile in profiles.values():
        if profile.isin:
            by_isin.setdefault(_clean(profile.isin), profile.id)
    _attach_holdings(bind, profiles, by_isin)
    _clean_sources(bind, profiles, by_isin)
    _retire_system_profiles(bind, profiles)


def downgrade() -> None:
    """Sans effet : les profils livrés avec l'application ne reviennent pas."""
