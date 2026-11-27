"""Composition d'un ETF : chaîne des sources (émetteurs, justETF puis Yahoo), fonds synthétiques décomposés
selon leur indice, agrégats du profil et référentiel des titres.

Tout le réseau est lu avant la première écriture ; une actualisation ne fait qu'un commit.
Une composition obtenue n'est jamais vidée ni appauvrie parce qu'une source répond mal."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain import etf_composition as rules
from app.domain.etf_normalize import UNKNOWN_LABEL, index_for_fund_name
from app.domain.etf_profiles import REFRESH_INTERVAL, SOURCE_YAHOO, apply_composition
from app.integrations import yahoo_finance
from app.integrations.etf_providers.amundi import Amundi
from app.integrations.etf_providers.base import (
    Composition,
    Constituent,
    FundCompositionMissing,
    Provider,
    ProviderFund,
    ProviderUnavailable,
)
from app.integrations.etf_providers.ishares import IShares
from app.integrations.etf_providers.justetf import JustEtf
from app.integrations.etf_providers.spdr import Spdr
from app.models.etf_profile import EtfProfile
from app.repositories.investissement import etf_constituents
from app.repositories.investissement import etf_profiles as repo
from app.repositories.investissement import securities as securities_repo

logger = get_logger(__name__)

# Dans l'ordre d'interrogation. Une instance par processus : le cache des catalogues survit d'un passage à l'autre.
PROVIDERS: list[Provider] = [IShares(), Amundi(), Spdr(), JustEtf()]


class CompositionUnavailable(Exception):
    """Rien d'exploitable alors qu'une source a failli : la composition connue reste, nouvel essai plus tard."""


@dataclass(frozen=True)
class _Found:
    source: str
    fund: ProviderFund | None = None
    composition: Composition | None = None
    # Composition Yahoo (secteurs, premières lignes, nom du fonds)
    yahoo: dict[str, Any] | None = None
    synthetic: bool = False

    @property
    def fund_name(self) -> str | None:
        return self.fund.name if self.fund else (self.yahoo or {}).get("name")

    @property
    def index_name(self) -> str | None:
        return (self.fund.index_name or index_for_fund_name(self.fund.name)) if self.fund else None


@dataclass
class _Pass:
    """État d'un passage : les sources injoignables (`down`) ne sont pas redemandées avant le suivant."""

    providers: Sequence[Provider]
    down: set[str]


def _ordered(providers: Sequence[Provider], remembered: str | None) -> list[Provider]:
    """La source déjà connue d'abord, si elle publie toutes les lignes (sinon un repli resterait préféré à jamais)."""
    if remembered not in rules.LINE_SOURCES:
        return list(providers)
    return sorted(providers, key=lambda p: p.name != remembered)


def _fallback_allowed(profile: EtfProfile, failed: set[str]) -> bool:
    """Des agrégats ne remplacent jamais des lignes, ni la source habituelle en panne, ni le profil d'un synthétique."""
    return not profile.lines_count and profile.replication != "synthetic" and profile.provider not in failed


async def _from_provider(profile: EtfProfile, provider: Provider, isin: str, failed: set[str]) -> _Found | None:
    """None : cette source n'a rien d'utilisable pour ce fonds. Lève `ProviderUnavailable` si elle est en panne."""
    fund = await provider.lookup(isin)
    if fund is None:
        return None
    if fund.replication == "synthetic" or (fund.replication == "unknown" and rules.looks_synthetic(fund.name)):
        # Le panier détenu par un fonds à swap ne dit rien de son exposition : il n'est même pas demandé
        if provider.name not in rules.LINE_SOURCES and (profile.lines_count or profile.provider in failed):
            return None  # un repli ne défait pas ce qu'on tient d'un émetteur momentanément en défaut
        return _Found(provider.name, fund=fund, synthetic=True)
    composition = await provider.fetch(fund)
    if composition.lines:
        if rules.is_usable(composition.lines):
            return _Found(provider.name, fund=fund, composition=composition)
        logger.warning(f"Composition {provider.name} écartée pour {isin} : somme des poids sous {rules.MIN_TOTAL_WEIGHT} %")
        failed.add(provider.name)
        return None
    return _Found(provider.name, fund=fund, composition=composition) if _fallback_allowed(profile, failed) else None


async def _collect(profile: EtfProfile, run: _Pass) -> _Found | None:
    """Interroge les sources sans rien écrire. None : aucune ne publie ce fonds."""
    failed: set[str] = set()
    isin = profile.isin
    for provider in _ordered(run.providers, profile.provider) if isin else []:
        if provider.name in run.down:
            failed.add(provider.name)
            continue
        try:
            found = await _from_provider(profile, provider, str(isin), failed)
        except FundCompositionMissing as e:
            logger.info(f"{provider.name} ne publie rien pour {isin} : {e}")  # source suivante, l'émetteur reste joignable
            continue
        except ProviderUnavailable as e:
            logger.warning(f"{provider.name} indisponible pour {isin} : {e}")
            run.down.add(provider.name)
            failed.add(provider.name)
            continue
        if found:
            return found
    if _fallback_allowed(profile, failed) and not rules.looks_synthetic(profile.name):
        if SOURCE_YAHOO in run.down:
            failed.add(SOURCE_YAHOO)
        else:
            try:
                composition = await yahoo_finance.fetch_composition(profile.ticker)
            except yahoo_finance.YahooUnavailable as e:
                logger.warning(f"Yahoo indisponible pour {profile.ticker} : {e}")
                run.down.add(SOURCE_YAHOO)
                failed.add(SOURCE_YAHOO)
            else:
                if composition:
                    return _Found(SOURCE_YAHOO, yahoo=composition)
    if failed:
        raise CompositionUnavailable(f"{profile.name} : sources en échec ({', '.join(sorted(failed))})")
    return None


def remember_securities(db: Session, lines: Sequence[Constituent], source: str) -> None:
    """Les actions d'une composition alimentent le référentiel des titres (pas de commit)."""
    securities_repo.upsert_many(db, [
        {"isin": x.isin, "ticker": (x.ticker or "").upper(), "exchange": x.exchange, "name": x.name,
         "country": x.country, "sector": None if x.sector == UNKNOWN_LABEL else x.sector, "source": source}
        for x in lines if x.isin and rules.is_equity(x)
    ])


def _describe(profile: EtfProfile, found: _Found) -> None:
    profile.provider = found.source
    fund = found.fund
    profile.provider_ref = fund.ref if fund else None
    profile.replication = fund.replication if fund else "unknown"
    profile.index_name = found.index_name
    profile.exposure_profile_id = None


def _apply(db: Session, profile: EtfProfile, found: _Found) -> list[str]:
    """Écrit une composition détenue (lignes d'un émetteur, ou agrégats de justETF / Yahoo)."""
    composition = found.composition
    if composition and composition.lines:
        updated = apply_composition(profile, rules.aggregate_lines(composition.lines), found.source, complete=True)
        etf_constituents.replace(db, profile.id, composition.lines)
        remember_securities(db, composition.lines, found.source)
        profile.coverage_pct = rules.coverage_of_lines(composition.lines)
        profile.lines_count = len(composition.lines)
    else:
        values = found.yahoo or {}
        if composition:
            values = {"countries": composition.countries, "sectors": composition.sectors,
                      "top_holdings": composition.top_holdings}
        updated = apply_composition(profile, values, found.source)
        if not updated:
            return updated
        profile.coverage_pct = rules.coverage_of_aggregates(values)
    _describe(profile, found)
    profile.composition_as_of = composition.as_of if composition else utcnow_naive().date()
    return updated


def _apply_synthetic(db: Session, profile: EtfProfile, found: _Found, reference: EtfProfile | None) -> None:
    """Un synthétique n'a ni lignes ni chiffres à lui : son exposition est celle de l'ETF de référence de l'indice."""
    apply_composition(profile, {}, complete=True)
    etf_constituents.replace(db, profile.id, [])
    _describe(profile, found)
    profile.replication = "synthetic"
    profile.lines_count = 0
    profile.exposure_profile_id = reference.id if reference else None
    profile.composition_as_of = reference.composition_as_of if reference else None
    profile.coverage_pct = (reference.coverage_pct or 0.0) if reference else 0.0


def _is_stale(profile: EtfProfile, before: timedelta = REFRESH_INTERVAL) -> bool:
    return not profile.composition_refreshed_at or profile.composition_refreshed_at <= utcnow_naive() - before


@dataclass(frozen=True)
class _Reference:
    profile: EtfProfile
    found: _Found | None
    # Faux : rien à écrire sur la référence (à jour, ou ses sources ont failli)
    read: bool


async def _prepare_reference(db: Session, synthetic: EtfProfile, index_name: str | None, run: _Pass) -> _Reference | None:
    """Profil de l'ETF physique qui suit le même indice, retrouvé ou à créer, relu s'il est périmé (sans écriture)."""
    isin = rules.INDEX_REFERENCES.get(index_name or "")
    if not index_name or not isin or isin == synthetic.isin:
        return None
    reference = repo.find_by_isin(db, isin) or EtfProfile(
        name=index_name, ticker=isin, isin=isin, aliases=f'["{isin}"]', countries="{}", sectors="{}",
        top_holdings="[]", composition_sources="{}", replication="unknown", lines_count=0, is_system=False,
    )
    if reference.replication == "synthetic":
        return None
    if not _is_stale(reference):
        return _Reference(reference, None, read=False)
    try:
        found = await _collect(reference, run)
    except CompositionUnavailable as e:
        logger.warning(f"Référence d'indice non relue : {e}")
        return _Reference(reference, None, read=False)
    if found and found.synthetic:
        return None
    return _Reference(reference, found, read=True)


def _save_reference(db: Session, reference: _Reference) -> EtfProfile:
    profile = reference.profile
    if profile.id is None:
        repo.add(db, profile)
        repo.flush(db)
    if reference.read:
        if reference.found:
            _apply(db, profile, reference.found)
        profile.composition_refreshed_at = utcnow_naive()
    return profile


async def refresh(
    db: Session, profile: EtfProfile, providers: Sequence[Provider] | None = None, *,
    down: set[str] | None = None, adopt_name: bool = False,
) -> list[str]:
    """Actualise la composition d'un profil (et de sa référence d'indice s'il est synthétique), puis valide.

    Renvoie les champs mis à jour. Lève `CompositionUnavailable` sans rien écrire.
    `adopt_name` : le profil prend le nom publié du fonds (création sans nom saisi)."""
    run = _Pass(PROVIDERS if providers is None else providers, set() if down is None else down)
    found = await _collect(profile, run)
    updated: list[str] = []
    if found and found.synthetic:
        prepared = await _prepare_reference(db, profile, found.index_name, run)
        reference = _save_reference(db, prepared) if prepared else None
        _apply_synthetic(db, profile, found, reference)
    elif found:
        updated = _apply(db, profile, found)
    if adopt_name and found and found.fund_name:
        profile.name = found.fund_name
    profile.composition_refreshed_at = utcnow_naive()
    db.commit()
    logger.info(f"ETF profile #{profile.id} ({profile.ticker}) refreshed from {found.source if found else 'nulle part'}: "
                f"{updated or 'aucun champ'}")
    return updated
