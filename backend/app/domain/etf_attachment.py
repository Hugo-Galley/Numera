"""Rattachement d'une position au profil ETF de son propre fonds (sans base).

Règles :
- une position dont l'ISIN est connu (le sien, ou celui contenu dans son symbole) et qui est rattachée à un profil
  qui porte un autre ISIN, ou à un profil système, va au profil de son ISIN, créé une seule fois s'il n'existe pas ;
  un profil saisi sans ISIN (non système) est un rattachement manuel : la position n'en part pas ;
- sans profil, elle ne rejoint qu'un profil existant ou créé dans le même passage pour une autre position (une
  action en direct a aussi un ISIN : rien n'est créé pour elle) ;
- sans ISIN, elle ne reste sur un profil système que si son ticker est le ticker propre du profil : les alias livrés
  mélangeaient plusieurs fonds et ne valent plus rien ; un rattachement à un autre profil n'est pas touché.

La migration `e1b7c4a9f2d6` recopie ces règles (une migration n'importe pas `app.*`).
"""
from collections.abc import Sequence
from typing import NamedTuple

from app.domain.holdings import normalize_ticker
from app.domain.isin import is_valid_isin, isin_from_symbol


class HoldingRef(NamedTuple):
    id: int
    ticker: str
    isin: str | None
    etf_profile_id: int | None


class ProfileRef(NamedTuple):
    id: int
    ticker: str
    isin: str | None
    is_system: bool


class AttachmentPlan(NamedTuple):
    moves: dict[int, int]  # position -> profil existant
    create_isins: set[str]  # profils à créer, un par ISIN
    pending: dict[int, str]  # position -> ISIN du profil à créer
    detach: set[int]


def _clean(isin: str | None) -> str:
    return (isin or "").upper().strip()


def _fund_isin(holding: HoldingRef) -> str | None:
    isin = _clean(holding.isin)
    return isin if is_valid_isin(isin) else isin_from_symbol(holding.ticker)


def _is_own_ticker(profile: ProfileRef, ticker: str) -> bool:
    return normalize_ticker(ticker) == normalize_ticker(profile.ticker)


def _leaves(profile: ProfileRef, isin: str) -> bool:
    """Vrai si une position d'ISIN `isin` doit quitter ce profil pour celui de son fonds."""
    own = _clean(profile.isin)
    return own != isin and (profile.is_system or bool(own))


def plan_attachments(holdings: Sequence[HoldingRef], profiles: Sequence[ProfileRef]) -> AttachmentPlan:
    by_id = {p.id: p for p in profiles}
    by_isin: dict[str, int] = {}
    for profile in sorted(profiles, key=lambda p: p.id):
        if profile.isin:
            by_isin.setdefault(_clean(profile.isin), profile.id)
    plan = AttachmentPlan({}, set(), {}, set())
    unattached: dict[int, str] = {}
    for holding in holdings:
        current = by_id.get(holding.etf_profile_id or 0)
        isin = _fund_isin(holding)
        if not isin:
            if current and current.is_system and not _is_own_ticker(current, holding.ticker):
                plan.detach.add(holding.id)
        elif current is None:
            if isin in by_isin:
                plan.moves[holding.id] = by_isin[isin]
            else:
                unattached[holding.id] = isin
        elif _leaves(current, isin):
            if isin in by_isin:
                plan.moves[holding.id] = by_isin[isin]
            else:
                plan.create_isins.add(isin)
                plan.pending[holding.id] = isin
    plan.pending.update({hid: isin for hid, isin in unattached.items() if isin in plan.create_isins})
    return plan
