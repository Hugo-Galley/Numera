"""Profils ETF : saisie, actualisation des compositions, création à la volée. Aucun n'est livré avec l'application."""
import json
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import ExternalServiceError, InvalidOperationError, NotFoundError
from app.core.i18n import tr
from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain.etf_profiles import (
    COMPOSITION_FIELDS,
    REFRESH_INTERVAL,
    SOURCE_MANUAL,
    apply_update,
    forget_composition_origin,
    to_read,
)
from app.integrations.etf_providers.base import Provider
from app.models.etf_profile import EtfProfile
from app.repositories.investissement import etf_constituents
from app.repositories.investissement import etf_profiles as repo
from app.schemas.etf_profile import AutoDecomposeRequest, EtfProfileCreate, EtfProfileRead, EtfProfileUpdate
from app.services.investissement import etf_composition

logger = get_logger(__name__)


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


def list_profiles(db: Session) -> list[EtfProfileRead]:
    profiles = repo.list_ordered(db)
    names = {p.id: p.name for p in profiles}
    return [to_read(p, names.get(p.exposure_profile_id or 0)) for p in profiles]


def _read(db: Session, profile: EtfProfile) -> EtfProfileRead:
    exposure = repo.get(db, profile.exposure_profile_id) if profile.exposure_profile_id else None
    return to_read(profile, exposure.name if exposure else None)


def _get(db: Session, profile_id: int) -> EtfProfile:
    profile = repo.get(db, profile_id)
    if not profile:
        raise NotFoundError(tr("errors.etf_profile_not_found"))
    return profile


def get_profile(db: Session, profile_id: int) -> EtfProfileRead:
    return _read(db, _get(db, profile_id))


def create_profile(db: Session, payload: EtfProfileCreate) -> EtfProfileRead:
    if repo.find_by_ticker_or_name(db, payload.ticker.upper(), payload.name):
        raise InvalidOperationError(tr("errors.etf_profile_exists"))
    profile = new_profile(payload)
    repo.add(db, profile)
    db.commit()
    db.refresh(profile)
    return _read(db, profile)


def update_profile(db: Session, profile_id: int, payload: EtfProfileUpdate) -> EtfProfileRead:
    profile = _get(db, profile_id)
    previous_isin = profile.isin
    apply_update(profile, payload)
    if profile.isin != previous_isin:
        if previous_isin:
            forget_composition_origin(profile)
            etf_constituents.replace(db, profile.id, [])
        else:
            profile.composition_refreshed_at = None  # fonds désormais identifié : relu au prochain passage
    db.commit()
    db.refresh(profile)
    return _read(db, profile)


def delete_profile(db: Session, profile_id: int) -> None:
    repo.delete(db, _get(db, profile_id))
    db.commit()


async def refresh_profile(db: Session, profile_id: int) -> EtfProfileRead:
    """Actualise la composition d'un profil depuis son émetteur (à défaut justETF puis Yahoo)."""
    profile = _get(db, profile_id)
    try:
        await etf_composition.refresh(db, profile)
    except etf_composition.CompositionUnavailable:
        raise ExternalServiceError(tr("errors.etf_sources_unreachable")) from None
    db.refresh(profile)
    return _read(db, profile)


async def _refresh_if_due(
    db: Session, profile: EtfProfile, threshold: datetime, providers: Sequence[Provider] | None, down: set[str]
) -> bool:
    if profile.composition_refreshed_at and profile.composition_refreshed_at > threshold:
        return False
    try:
        await etf_composition.refresh(db, profile, providers, down=down)
    except etf_composition.CompositionUnavailable as e:
        logger.warning(f"Composition non actualisée : {e}")
        return False
    return True


async def refresh_held_etf_profiles(
    db: Session, force: bool = False, providers: Sequence[Provider] | None = None
) -> int:
    """Actualise les profils détenus, puis leurs références d'indice, dont la composition date de plus de
    REFRESH_INTERVAL (tâche de fond). Une source injoignable est sautée jusqu'au passage suivant."""
    start = utcnow_naive()
    # `force` : tout ce qui n'a pas déjà été relu pendant ce passage
    threshold = start if force else start - REFRESH_INTERVAL
    down: set[str] = set()
    held = repo.held_profiles(db)
    refreshed = 0
    for profile in held:
        refreshed += await _refresh_if_due(db, profile, threshold, providers, down)
    held_ids = {p.id for p in held}
    exposure_ids = {p.exposure_profile_id for p in held if p.exposure_profile_id} - held_ids
    for reference in repo.get_many(db, exposure_ids):
        refreshed += await _refresh_if_due(db, reference, threshold, providers, down)
    return refreshed


async def auto_decompose_and_create_profile(
    db: Session,
    symbol: str,
    name: str | None = None,
    isin: str | None = None
) -> EtfProfile | None:
    """Crée un profil pour un ETF ou fonds inconnu, puis lit sa composition (émetteur, justETF ou Yahoo).

    Les champs qu'aucune source ne publie restent vides.
    """
    cleaned_sym = symbol.strip().upper()

    existing = repo.find_by_symbol_or_alias(db, cleaned_sym)
    if existing:
        return existing

    aliases = [cleaned_sym]
    if isin:
        aliases.append(isin.upper())

    try:
        profile = EtfProfile(
            name=name or cleaned_sym,
            ticker=cleaned_sym,
            isin=isin.upper() if isin else None,
            aliases=json.dumps(aliases),
            countries="{}",
            sectors="{}",
            top_holdings="[]",
            composition_sources="{}",
            is_system=False,
        )
        repo.add(db, profile)
        db.commit()
        db.refresh(profile)
        # Rattache les positions existantes de même ticker
        repo.attach_to_holdings(db, cleaned_sym, profile.id)
        db.commit()
        logger.info(f"Created ETF profile {profile.name} (#{profile.id})")
        try:
            await etf_composition.refresh(db, profile, adopt_name=not name)
        except etf_composition.CompositionUnavailable as e:
            logger.warning(f"Composition pas encore disponible : {e}")
        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error persisting ETF profile for {cleaned_sym}: {e}", exc_info=True)
        return None


async def auto_decompose(db: Session, payload: AutoDecomposeRequest) -> EtfProfileRead:
    """Crée le profil d'un ETF ou fonds inconnu à partir de sa composition publiée."""
    profile = await auto_decompose_and_create_profile(db=db, symbol=payload.symbol, name=payload.name, isin=payload.isin)
    if not profile:
        raise InvalidOperationError(tr("errors.etf_decompose_failed"))
    return _read(db, profile)
