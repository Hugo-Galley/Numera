"""Profils ETF : correspondance d'un titre avec un profil connu, sources de la composition, lecture et saisie.

Chaque champ de composition garde sa source dans `EtfProfile.composition_sources` :
- `yahoo` : remplacé à chaque actualisation ;
- `preset` : préréglage des profils système (`etf_presets.json`), utilisé en repli tant que Yahoo
  ne fournit pas le champ ;
- `manual` : saisi par l'utilisateur, jamais écrasé.
"""
import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.core.time import utcnow_naive
from app.models.etf_profile import EtfProfile
from app.schemas.etf_profile import EtfProfileCreate, EtfProfileRead, EtfProfileUpdate

SOURCE_YAHOO = "yahoo"
SOURCE_PRESET = "preset"
SOURCE_MANUAL = "manual"
COMPOSITION_FIELDS = ("countries", "sectors", "top_holdings")
# Champs que Yahoo sait fournir (jamais les pays)
YAHOO_FIELDS = ("sectors", "top_holdings")

# Les compositions publiées bougent peu : une actualisation hebdomadaire suffit
REFRESH_INTERVAL = timedelta(days=7)


def load_sources(profile: EtfProfile) -> Dict[str, str]:
    try:
        sources = json.loads(profile.composition_sources or "{}")
        return sources if isinstance(sources, dict) else {}
    except (TypeError, ValueError):
        return {}


def apply_composition(profile: EtfProfile, composition: Dict[str, Any]) -> List[str]:
    """Écrit les champs fournis par Yahoo, sauf ceux saisis à la main. Renvoie les champs mis à jour."""
    sources = load_sources(profile)
    updated: List[str] = []
    for field in YAHOO_FIELDS:
        value = composition.get(field)
        if not value or sources.get(field) == SOURCE_MANUAL:
            continue
        setattr(profile, field, json.dumps(value, ensure_ascii=False))
        sources[field] = SOURCE_YAHOO
        updated.append(field)
    profile.composition_sources = json.dumps(sources)
    profile.composition_refreshed_at = utcnow_naive()
    return updated


def to_read(profile: EtfProfile) -> EtfProfileRead:
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
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def new_profile(payload: EtfProfileCreate) -> EtfProfile:
    """Profil saisi par l'utilisateur : les champs de composition fournis sont marqués `manual`."""
    return EtfProfile(
        name=payload.name,
        ticker=payload.ticker.upper(),
        isin=payload.isin.upper() if payload.isin else None,
        aliases=json.dumps(payload.aliases or [payload.ticker.upper()]),
        countries=json.dumps(payload.countries or {}),
        sectors=json.dumps(payload.sectors or {}),
        top_holdings=json.dumps([h.model_dump() for h in payload.top_holdings]),
        composition_sources=json.dumps({
            field: SOURCE_MANUAL for field in COMPOSITION_FIELDS if getattr(payload, field)
        }),
        is_system=False,
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

    # Un champ de composition saisi à la main n'est plus écrasé par l'actualisation Yahoo
    sources = load_sources(profile)
    for field in COMPOSITION_FIELDS:
        if getattr(payload, field) is not None:
            sources[field] = SOURCE_MANUAL
    profile.composition_sources = json.dumps(sources)


def match_profile(profiles: List[EtfProfile], symbol: str, isin: Optional[str] = None, name: Optional[str] = None) -> Optional[EtfProfile]:
    """Find matching EtfProfile by ticker, isin or alias."""
    norm_symbol = symbol.upper().strip()
    norm_isin = (isin or "").upper().strip()
    norm_name = (name or "").lower().strip()

    # Exact isin or ticker match
    for p in profiles:
        if norm_isin and p.isin and p.isin.upper() == norm_isin:
            return p
        if p.ticker.upper() == norm_symbol:
            return p

        # Check aliases
        try:
            aliases = json.loads(p.aliases)
            for alias in aliases:
                if alias.upper() in (norm_symbol, norm_symbol.split(".")[0], norm_isin):
                    return p
        except Exception:
            pass

    # Name-based heuristic : nom vide => aucune correspondance (sinon "" est contenu dans tout),
    # et on exige que le nom complet du profil figure dans le libellé (pas l'inverse, trop large)
    if not norm_name:
        return None
    for p in profiles:
        p_name = p.name.lower().strip()
        if len(p_name) >= 6 and (p_name == norm_name or p_name in norm_name):
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
        try:
            aliases = [a.lower() for a in json.loads(p.aliases)]
            if any(q_lower in a or a in q_lower for a in aliases):
                matches = True
        except Exception:
            pass
    return bool(matches)
