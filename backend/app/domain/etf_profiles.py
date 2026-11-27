"""Profils ETF : correspondance d'un titre avec un profil connu, sources de la composition, lecture et saisie.

Chaque champ de composition garde sa source dans `EtfProfile.composition_sources` :
- `ishares`, `amundi`, `spdr`, `justetf`, `yahoo` : remplacé à chaque actualisation ;
- `manual` : saisi par l'utilisateur, jamais écrasé.
"""
from __future__ import annotations

import json
from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from app.core.time import utcnow_naive
from app.schemas.etf_profile import EtfProfileRead, EtfProfileUpdate

if TYPE_CHECKING:
    from app.models.etf_profile import EtfProfile

SOURCE_YAHOO = "yahoo"
SOURCE_MANUAL = "manual"
COMPOSITION_FIELDS = ("countries", "sectors", "top_holdings")
EMPTY_FIELDS = {"countries": "{}", "sectors": "{}", "top_holdings": "[]"}

# Les émetteurs publient leur composition chaque jour
REFRESH_INTERVAL = timedelta(days=1)


def load_sources(profile: EtfProfile) -> dict[str, str]:
    try:
        sources = json.loads(profile.composition_sources or "{}")
        return sources if isinstance(sources, dict) else {}
    except (TypeError, ValueError):
        return {}


def apply_composition(
    profile: EtfProfile, composition: dict[str, Any], source: str = SOURCE_YAHOO, *, complete: bool = False
) -> list[str]:
    """Écrit les champs fournis par `source`, sauf ceux saisis à la main. Renvoie les champs mis à jour.

    `complete` : la source décrit tout le fonds, un champ qu'elle ne renseigne pas est vidé."""
    sources = load_sources(profile)
    updated: list[str] = []
    for field in COMPOSITION_FIELDS:
        value = composition.get(field)
        if sources.get(field) == SOURCE_MANUAL:
            continue
        if value:
            setattr(profile, field, json.dumps(value, ensure_ascii=False))
            sources[field] = source
            updated.append(field)
        elif complete:
            setattr(profile, field, EMPTY_FIELDS[field])
            sources.pop(field, None)
    profile.composition_sources = json.dumps(sources)
    profile.composition_refreshed_at = utcnow_naive()
    return updated


def forget_composition_origin(profile: EtfProfile) -> None:
    """L'ISIN a changé : ce qu'on savait de l'ancien fonds (hors saisie manuelle) ne vaut plus."""
    apply_composition(profile, {}, complete=True)
    profile.provider = profile.provider_ref = profile.index_name = None
    profile.replication = "unknown"
    profile.exposure_profile_id = None
    profile.composition_as_of = None
    profile.coverage_pct = None
    profile.lines_count = 0
    profile.composition_refreshed_at = None


def to_read(profile: EtfProfile, exposure_name: str | None = None) -> EtfProfileRead:
    """`exposure_name` : nom du profil de référence d'un synthétique (`exposure_profile_id`)."""
    return EtfProfileRead(
        id=profile.id,
        name=profile.name,
        ticker=profile.ticker,
        isin=profile.isin,
        aliases=json.loads(profile.aliases) if profile.aliases else [],
        countries=json.loads(profile.countries) if profile.countries else {},
        sectors=json.loads(profile.sectors) if profile.sectors else {},
        top_holdings=json.loads(profile.top_holdings) if profile.top_holdings else [],
        is_system=profile.is_system,
        composition_sources=load_sources(profile),
        composition_refreshed_at=profile.composition_refreshed_at,
        provider=profile.provider,
        replication=profile.replication,
        index_name=profile.index_name,
        exposure_profile_id=profile.exposure_profile_id,
        exposure_profile_name=exposure_name,
        composition_as_of=profile.composition_as_of,
        coverage_pct=profile.coverage_pct,
        lines_count=profile.lines_count,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def apply_update(profile: EtfProfile, payload: EtfProfileUpdate) -> None:
    if payload.name is not None:
        profile.name = payload.name
    if payload.ticker is not None:
        profile.ticker = payload.ticker.upper()
    if payload.isin is not None:
        profile.isin = payload.isin.upper() if payload.isin else None
    if payload.aliases is not None:
        profile.aliases = json.dumps(payload.aliases)
    if payload.countries is not None:
        profile.countries = json.dumps(payload.countries)
    if payload.sectors is not None:
        profile.sectors = json.dumps(payload.sectors)
    if payload.top_holdings is not None:
        profile.top_holdings = json.dumps([h.model_dump() for h in payload.top_holdings])

    # Un champ de composition saisi à la main n'est plus écrasé par l'actualisation
    sources = load_sources(profile)
    for field in COMPOSITION_FIELDS:
        if getattr(payload, field) is not None:
            sources[field] = SOURCE_MANUAL
    profile.composition_sources = json.dumps(sources)


def match_profile(profiles: list[EtfProfile], symbol: str, isin: str | None = None, name: str | None = None) -> EtfProfile | None:
    """Profil correspondant exactement : ISIN, puis ticker, puis alias (casse ignorée).

    Jamais de ticker tronqué ni de rapprochement par nom : `name` est conservé pour les appelants et ignoré.
    """
    norm_symbol = symbol.upper().strip()
    norm_isin = (isin or "").upper().strip()

    if norm_isin:
        for p in profiles:
            if p.isin and p.isin.upper() == norm_isin:
                return p
    for p in profiles:
        if p.ticker.upper() == norm_symbol:
            return p
    for p in profiles:
        with suppress(Exception):  # alias illisible : ignoré
            if any(str(alias).upper().strip() == norm_symbol for alias in json.loads(p.aliases)):
                return p
    return None


def profile_matches_query(p: EtfProfile, q_lower: str) -> bool:
    """Vrai si la recherche (en minuscules) vise ce profil : nom, ticker, ISIN ou alias."""
    p_name = p.name.lower()
    p_ticker = p.ticker.lower()
    p_isin = (p.isin or "").lower()

    matches = (
        q_lower in p_name
        or q_lower == p_ticker
        or q_lower in p_ticker
        or (p_isin and q_lower == p_isin)
    )
    if not matches:
        with suppress(Exception):  # alias illisible : ignoré
            aliases = [a.lower() for a in json.loads(p.aliases)]
            if any(q_lower in a or a in q_lower for a in aliases):
                matches = True
    return bool(matches)
