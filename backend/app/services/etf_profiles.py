"""Profils ETF : saisie, actualisation de la composition depuis Yahoo, création à la volée, profils système."""
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.errors import ExternalServiceError, InvalidOperationError, NotFoundError
from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain.etf_presets import SYSTEM_ETF_PRESETS
from app.domain.etf_profiles import (
    COMPOSITION_FIELDS,
    REFRESH_INTERVAL,
    SOURCE_PRESET,
    apply_composition,
    apply_update,
    load_sources,
    new_profile,
    to_read,
)
from app.integrations import yahoo_finance
from app.models.etf_profile import EtfProfile
from app.repositories import etf_profiles as repo
from app.schemas.etf_profile import AutoDecomposeRequest, EtfProfileCreate, EtfProfileRead, EtfProfileUpdate

logger = get_logger(__name__)


def list_profiles(db: Session) -> List[EtfProfileRead]:
    return [to_read(p) for p in repo.list_ordered(db)]


def _get(db: Session, profile_id: int) -> EtfProfile:
    profile = repo.get(db, profile_id)
    if not profile:
        raise NotFoundError("ETF profile not found")
    return profile


def get_profile(db: Session, profile_id: int) -> EtfProfileRead:
    return to_read(_get(db, profile_id))


def create_profile(db: Session, payload: EtfProfileCreate) -> EtfProfileRead:
    if repo.find_by_ticker_or_name(db, payload.ticker.upper(), payload.name):
        raise InvalidOperationError("An ETF profile with this name or ticker already exists")
    profile = new_profile(payload)
    repo.add(db, profile)
    db.commit()
    db.refresh(profile)
    return to_read(profile)


def update_profile(db: Session, profile_id: int, payload: EtfProfileUpdate) -> EtfProfileRead:
    profile = _get(db, profile_id)
    apply_update(profile, payload)
    db.commit()
    db.refresh(profile)
    return to_read(profile)


def delete_profile(db: Session, profile_id: int) -> None:
    profile = _get(db, profile_id)
    if profile.is_system:
        raise InvalidOperationError("Cannot delete system preset ETF profiles")
    repo.delete(db, profile)
    db.commit()


async def refresh_etf_profile(db: Session, profile: EtfProfile) -> List[str]:
    """Actualise un profil depuis Yahoo. Lève YahooUnavailable si Yahoo est injoignable."""
    composition = await yahoo_finance.fetch_composition(profile.ticker)
    updated = apply_composition(profile, composition or {})
    db.commit()
    logger.info(f"ETF profile #{profile.id} ({profile.ticker}) refreshed from Yahoo: {updated or 'aucune donnée'}")
    return updated


async def refresh_profile(db: Session, profile_id: int) -> EtfProfileRead:
    """Actualise la composition d'un profil depuis Yahoo (secteurs et top 10 ; jamais les pays)."""
    profile = _get(db, profile_id)
    try:
        await refresh_etf_profile(db, profile)
    except yahoo_finance.YahooUnavailable:
        raise ExternalServiceError("Yahoo Finance est injoignable, réessayez plus tard")
    db.refresh(profile)
    return to_read(profile)


async def refresh_held_etf_profiles(db: Session, force: bool = False) -> int:
    """Actualise les profils détenus dont la composition date de plus de REFRESH_INTERVAL (tâche de fond)."""
    threshold = utcnow_naive() - REFRESH_INTERVAL
    refreshed = 0
    for profile in repo.held_profiles(db):
        if not force and profile.composition_refreshed_at and profile.composition_refreshed_at > threshold:
            continue
        try:
            await refresh_etf_profile(db, profile)
            refreshed += 1
        except yahoo_finance.YahooUnavailable as e:
            logger.warning(f"Yahoo unavailable, ETF profile refresh stopped: {e}")
            break
    return refreshed


async def auto_decompose_and_create_profile(
    db: Session,
    symbol: str,
    name: Optional[str] = None,
    isin: Optional[str] = None
) -> Optional[EtfProfile]:
    """Crée un profil pour un ETF ou fonds inconnu à partir de la composition publiée par Yahoo.

    Les champs que Yahoo ne fournit pas (toujours les pays) restent vides.
    """
    cleaned_sym = symbol.strip().upper()

    existing = repo.find_by_symbol_or_alias(db, cleaned_sym)
    if existing:
        return existing

    try:
        composition = await yahoo_finance.fetch_composition(cleaned_sym)
    except yahoo_finance.YahooUnavailable as e:
        logger.warning(f"Could not fetch Yahoo composition for {cleaned_sym}: {e}")
        composition = None

    fund_name = name or (composition or {}).get("name") or cleaned_sym
    aliases = [cleaned_sym, cleaned_sym.split(".")[0], fund_name.upper()]
    if isin:
        aliases.append(isin.upper())

    try:
        profile = EtfProfile(
            name=fund_name,
            ticker=cleaned_sym,
            isin=isin.upper() if isin else None,
            aliases=json.dumps(aliases),
            countries="{}",
            sectors="{}",
            top_holdings="[]",
            composition_sources="{}",
            is_system=False,
        )
        if composition is not None:
            apply_composition(profile, composition)
        repo.add(db, profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Created ETF profile {profile.name} (#{profile.id}) from Yahoo composition")

        # Rattache les positions existantes de même ticker
        repo.attach_to_holdings(db, cleaned_sym, profile.id)
        db.commit()

        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error persisting ETF profile for {cleaned_sym}: {e}", exc_info=True)
        return None


async def auto_decompose(db: Session, payload: AutoDecomposeRequest) -> EtfProfileRead:
    """Crée le profil d'un ETF ou fonds inconnu à partir de la composition publiée par Yahoo."""
    profile = await auto_decompose_and_create_profile(db=db, symbol=payload.symbol, name=payload.name, isin=payload.isin)
    if not profile:
        raise InvalidOperationError("Could not decompose ETF profile online")
    return to_read(profile)


def seed_etf_profiles(db: Session) -> None:
    """
    Crée ou met à jour les profils ETF système.

    Les compositions de `etf_presets.json` ne sont qu'un repli : un champ actualisé depuis Yahoo
    ou saisi à la main n'est jamais réécrit (cf. `composition_sources`).
    """
    count = 0
    for preset in SYSTEM_ETF_PRESETS:
        existing = repo.find_by_name(db, preset["name"])
        if not existing:
            profile = EtfProfile(
                name=preset["name"],
                ticker=preset["ticker"],
                isin=preset["isin"],
                aliases=json.dumps(preset["aliases"]),
                countries=json.dumps(preset["countries"]),
                sectors=json.dumps(preset["sectors"]),
                top_holdings=json.dumps(preset["top_holdings"]),
                composition_sources=json.dumps({field: SOURCE_PRESET for field in COMPOSITION_FIELDS}),
                is_system=True,
            )
            repo.add(db, profile)
            count += 1
        elif existing.is_system:
            existing.ticker = preset["ticker"]
            existing.isin = preset["isin"]
            existing.aliases = json.dumps(preset["aliases"])
            sources = load_sources(existing)
            for field in COMPOSITION_FIELDS:
                if sources.get(field, SOURCE_PRESET) == SOURCE_PRESET:
                    setattr(existing, field, json.dumps(preset[field]))
                    sources[field] = SOURCE_PRESET
            existing.composition_sources = json.dumps(sources)

    db.commit()
    if count > 0:
        logger.info(f"Seeded {count} system ETF profiles.")
