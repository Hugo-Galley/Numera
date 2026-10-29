"""Recherche et validation de titres : profils ETF locaux puis recherche publique Yahoo."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.etf_profiles import match_profile, profile_matches_query
from app.domain.market import guess_quote_currency
from app.integrations import yahoo_finance
from app.models.etf_profile import EtfProfile
from app.repositories.investissement import etf_profiles as etf_repo
from app.services.investissement.market import quotes

logger = get_logger(__name__)


def match_etf_profile(db: Session, symbol: str, isin: Optional[str] = None, name: Optional[str] = None) -> Optional[EtfProfile]:
    """Profil ETF correspondant à un titre (ticker, ISIN, alias, puis nom)."""
    return match_profile(etf_repo.all_profiles(db), symbol, isin, name)


def _local_matches(db: Session, cleaned: str, seen_symbols: set) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    q_lower = cleaned.lower()
    for p in etf_repo.all_profiles(db):
        if profile_matches_query(p, q_lower):
            sym = p.ticker
            if sym not in seen_symbols:
                seen_symbols.add(sym)
                results.append({
                    "symbol": p.ticker,
                    "name": p.name,
                    "isin": p.isin,
                    "type": "ETF",
                    "exchange": "EUR",
                    "currency": "EUR",
                    "etf_profile_id": p.id,
                    "is_custom_etf": not p.is_system,
                })
    return results


async def _yahoo_matches(db: Optional[Session], cleaned: str, seen_symbols: set, results: List[Dict[str, Any]]) -> None:
    try:
        for q in await yahoo_finance.search_quotes(cleaned):
            sym = q.get("symbol")
            if not sym or sym in seen_symbols:
                continue

            # Filter out obscure or non-quote types if any
            q_type = q.get("quoteType", "EQUITY")
            short_name = q.get("shortname") or q.get("longname") or sym
            exchange = q.get("exchange", "")

            # Profil ETF déjà connu ; sinon il est créé quand le titre est réellement ajouté
            etf_profile = match_etf_profile(db, sym, None, short_name) if db else None

            seen_symbols.add(sym)
            results.append({
                "symbol": sym,
                "name": short_name,
                "isin": None,
                "type": q_type,
                "exchange": exchange,
                "currency": guess_quote_currency(sym),
                "etf_profile_id": etf_profile.id if etf_profile else None,
                "is_custom_etf": False,
            })
    except Exception as e:
        logger.warning(f"Error querying market search API for '{cleaned}': {e}")


async def search_market_assets(query: str, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Search for market assets by ISIN code, Ticker symbol or Name.
    Combines local ETF profiles and Yahoo Finance public search.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    seen_symbols: set = set()
    # 1. Search in local ETF profiles first
    results = _local_matches(db, cleaned, seen_symbols) if db else []
    # 2. Query Yahoo Finance public search API
    await _yahoo_matches(db, cleaned, seen_symbols, results)
    return results


def _invalid(symbol: str) -> Dict[str, Any]:
    return {
        "valid": False,
        "symbol": symbol,
        "name": None,
        "isin": None,
        "type": None,
        "currency": "EUR",
        "price": None,
        "price_eur": None,
        "etf_profile_id": None,
    }


def _best_match(assets: List[Dict[str, Any]], term: str) -> Optional[Dict[str, Any]]:
    for a in assets:
        if a["symbol"].upper() == term.upper() or (a.get("isin") and a["isin"].upper() == term.upper()):
            return a
    if assets:
        first = assets[0]
        if term.upper() in first["symbol"].upper() or (first.get("isin") and term.upper() == first["isin"].upper()):
            return first
    return None


async def validate_symbol(db: Session, symbol_or_isin: str) -> Dict[str, Any]:
    """Vérifie qu'un ticker ou un ISIN existe et renvoie ses informations (cours compris)."""
    term = symbol_or_isin.strip()
    if not term:
        return _invalid("")

    match = _best_match(await search_market_assets(term, db=db), term)
    if match:
        quote_data = await quotes.get_market_quotes([match["symbol"]])
        q_info = quote_data.get(match["symbol"].upper(), {})
        return {
            "valid": True,
            "symbol": match["symbol"],
            "name": match["name"],
            "isin": match.get("isin"),
            "type": match.get("type", "EQUITY"),
            "currency": q_info.get("currency") or match.get("currency", "EUR"),
            "price": q_info.get("price") if q_info.get("type") != "UNKNOWN" else None,
            "price_eur": q_info.get("price_eur") if q_info.get("type") != "UNKNOWN" else None,
            "etf_profile_id": match.get("etf_profile_id"),
        }

    found = await quotes.get_market_quotes([term])
    if term.upper() in found:
        q_info = found[term.upper()]
        if q_info.get("type") != "UNKNOWN" and (q_info.get("price") or 0) > 0:
            return {
                "valid": True,
                "symbol": term.upper(),
                "name": q_info.get("name", term.upper()),
                "isin": None,
                "type": q_info.get("type", "EQUITY"),
                "currency": q_info.get("currency", "EUR"),
                "price": q_info.get("price"),
                "price_eur": q_info.get("price_eur"),
                "etf_profile_id": None,
            }
    return _invalid(term.upper())
