"""Composition des ETF et fonds à partir de Yahoo Finance (module `topHoldings` de quoteSummary).

Yahoo fournit la répartition sectorielle et, pour les ETF à réplication physique, les 10 premières
lignes. Il ne fournit jamais la répartition par pays. Chaque champ de composition garde sa source
dans `EtfProfile.composition_sources` :
- `yahoo` : remplacé à chaque actualisation ;
- `preset` : préréglage des profils système (`seeds_etf.py`), utilisé en repli tant que Yahoo
  ne fournit pas le champ ;
- `manual` : saisi par l'utilisateur, jamais écrasé.
"""
import json
from datetime import timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

SOURCE_YAHOO = "yahoo"
SOURCE_PRESET = "preset"
SOURCE_MANUAL = "manual"
COMPOSITION_FIELDS = ("countries", "sectors", "top_holdings")
# Champs que Yahoo sait fournir (jamais les pays)
YAHOO_FIELDS = ("sectors", "top_holdings")

# Les compositions publiées bougent peu : une actualisation hebdomadaire suffit
REFRESH_INTERVAL = timedelta(days=7)

YAHOO_SECTOR_LABELS: Dict[str, str] = {
    "technology": "Technologie",
    "financial_services": "Finance",
    "healthcare": "Santé",
    "consumer_cyclical": "Consommation discrétionnaire",
    "consumer_defensive": "Biens de consommation",
    "industrials": "Industrie",
    "communication_services": "Services de communication",
    "basic_materials": "Matériaux",
    "energy": "Énergie",
    "utilities": "Services aux collectivités",
    "realestate": "Immobilier",
}

QUOTE_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"

# quoteSummary exige un cookie de consentement et un « crumb » associé ; on les garde en mémoire
_yahoo_auth: Dict[str, Any] = {"cookies": None, "crumb": None}


class YahooUnavailable(Exception):
    """Yahoo injoignable ou réponse inexploitable (différent de « pas de données pour ce titre »)."""


def load_sources(profile: EtfProfile) -> Dict[str, str]:
    try:
        sources = json.loads(profile.composition_sources or "{}")
        return sources if isinstance(sources, dict) else {}
    except (TypeError, ValueError):
        return {}


async def _ensure_crumb(client: httpx.AsyncClient, force: bool = False) -> str:
    if _yahoo_auth["crumb"] and not force:
        client.cookies.update(_yahoo_auth["cookies"])
        return _yahoo_auth["crumb"]
    # fc.yahoo.com répond 404 mais dépose le cookie A3 nécessaire au crumb
    # (le crumb est servi en text/plain : Accept: application/json donnerait un 406)
    await client.get("https://fc.yahoo.com", headers={"Accept": "*/*"}, follow_redirects=True)
    resp = await client.get("https://query2.finance.yahoo.com/v1/test/getcrumb", headers={"Accept": "*/*"})
    crumb = resp.text.strip()
    if resp.status_code != 200 or not crumb or "<" in crumb:
        raise YahooUnavailable(f"crumb Yahoo indisponible (HTTP {resp.status_code})")
    _yahoo_auth["crumb"] = crumb
    _yahoo_auth["cookies"] = dict(client.cookies)
    return crumb


def _parse_top_holdings(top: Dict[str, Any]) -> Dict[str, Any]:
    sectors: Dict[str, float] = {}
    for entry in top.get("sectorWeightings") or []:
        for key, value in entry.items():
            weight = round(float((value or {}).get("raw") or 0.0) * 100, 2)
            if weight > 0:
                label = YAHOO_SECTOR_LABELS.get(key, key.replace("_", " ").capitalize())
                sectors[label] = round(sectors.get(label, 0.0) + weight, 2)

    holdings: List[Dict[str, Any]] = []
    for h in top.get("holdings") or []:
        weight = round(float((h.get("holdingPercent") or {}).get("raw") or 0.0) * 100, 2)
        name = h.get("holdingName") or h.get("symbol")
        if name and weight > 0:
            holdings.append({"name": name, "ticker": h.get("symbol") or None, "weight": weight})

    return {"sectors": sectors, "top_holdings": holdings}


async def fetch_yahoo_composition(symbol: str) -> Optional[Dict[str, Any]]:
    """Composition publiée par Yahoo pour `symbol`.

    Renvoie None si Yahoo ne connaît pas le titre, un dict (éventuellement vide) sinon.
    Lève YahooUnavailable si Yahoo est injoignable.
    """
    cleaned = symbol.strip().upper()
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=8.0) as client:
            crumb = await _ensure_crumb(client)
            params = {"modules": "topHoldings,quoteType", "crumb": crumb}
            url = QUOTE_SUMMARY_URL.format(symbol=cleaned)
            resp = await client.get(url, params=params)
            if resp.status_code in (401, 403):
                params["crumb"] = await _ensure_crumb(client, force=True)
                resp = await client.get(url, params=params)
    except httpx.HTTPError as e:
        raise YahooUnavailable(str(e)) from e

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise YahooUnavailable(f"quoteSummary {cleaned} : HTTP {resp.status_code}")

    try:
        result = (resp.json().get("quoteSummary") or {}).get("result") or []
    except ValueError as e:
        raise YahooUnavailable(f"quoteSummary {cleaned} : réponse illisible") from e
    if not result:
        return None

    data = result[0]
    quote_type = data.get("quoteType") or {}
    composition = _parse_top_holdings(data.get("topHoldings") or {})
    composition["name"] = quote_type.get("longName") or quote_type.get("shortName")
    composition["quote_type"] = quote_type.get("quoteType")
    return composition


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


async def refresh_etf_profile(db: Session, profile: EtfProfile) -> List[str]:
    """Actualise un profil depuis Yahoo. Lève YahooUnavailable si Yahoo est injoignable."""
    composition = await fetch_yahoo_composition(profile.ticker)
    updated = apply_composition(profile, composition or {})
    db.commit()
    logger.info(f"ETF profile #{profile.id} ({profile.ticker}) refreshed from Yahoo: {updated or 'aucune donnée'}")
    return updated


def held_profiles(db: Session) -> List[EtfProfile]:
    """Profils rattachés à une position détenue."""
    ids = {
        pid for (pid,) in db.query(PortfolioHolding.etf_profile_id)
        .filter(PortfolioHolding.etf_profile_id.isnot(None), PortfolioHolding.quantity > 0)
        .distinct()
    }
    if not ids:
        return []
    return db.query(EtfProfile).filter(EtfProfile.id.in_(ids)).order_by(EtfProfile.name).all()


async def refresh_held_etf_profiles(db: Session, force: bool = False) -> int:
    """Actualise les profils détenus dont la composition date de plus de REFRESH_INTERVAL (tâche de fond)."""
    threshold = utcnow_naive() - REFRESH_INTERVAL
    refreshed = 0
    for profile in held_profiles(db):
        if not force and profile.composition_refreshed_at and profile.composition_refreshed_at > threshold:
            continue
        try:
            await refresh_etf_profile(db, profile)
            refreshed += 1
        except YahooUnavailable as e:
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

    existing = db.query(EtfProfile).filter(
        (EtfProfile.ticker.ilike(cleaned_sym)) |
        (EtfProfile.aliases.ilike(f'%"{cleaned_sym}"%'))
    ).first()
    if existing:
        return existing

    try:
        composition = await fetch_yahoo_composition(cleaned_sym)
    except YahooUnavailable as e:
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
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Created ETF profile {profile.name} (#{profile.id}) from Yahoo composition")

        # Rattache les positions existantes de même ticker
        db.query(PortfolioHolding).filter(
            PortfolioHolding.ticker.ilike(cleaned_sym),
            PortfolioHolding.etf_profile_id.is_(None)
        ).update({"etf_profile_id": profile.id}, synchronize_session=False)
        db.commit()

        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error persisting ETF profile for {cleaned_sym}: {e}", exc_info=True)
        return None
