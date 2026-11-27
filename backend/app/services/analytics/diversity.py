"""Scanner de diversification : expositions réelles par transparence des ETF, doublons, score et alertes,
rapportées au portefeuille boursier et au patrimoine total."""
from datetime import timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain.diversity import (
    Exposure,
    LookThrough,
    diversity_alerts,
    exposure_rows,
    look_through,
    top_companies,
)
from app.domain.diversity_score import hhi_score, score_label
from app.domain.etf_profiles import match_profile
from app.domain.holdings import holding_profile, is_crypto, is_etf_holding, is_fund
from app.domain.isin import IsinCandidate, pick_isin
from app.integrations import yahoo_finance
from app.integrations.currency import get_exchange_rates
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.security import Security
from app.repositories.analytics import diversity as repo
from app.repositories.comptes.balances import active_accounts
from app.repositories.investissement import etf_constituents
from app.repositories.investissement import etf_profiles as etf_repo
from app.repositories.investissement import securities as securities_repo
from app.services.comptes.wealth import account_values
from app.services.investissement.etf_profiles import auto_decompose_and_create_profile
from app.services.investissement.market import quotes as market_quotes

logger = get_logger(__name__)

PROFILE_RETRY = timedelta(days=7)


async def _resolve_profile(db: Session, h: PortfolioHolding, q: dict[str, Any],
                           profiles: list[EtfProfile]) -> EtfProfile | None:
    """Profil ETF de la position : rattaché, retrouvé (correspondance exacte), ou créé depuis Yahoo pour un fonds
    inconnu (seulement si le type du titre est un fonds ; rattachement commité)."""
    matched_p = holding_profile(profiles, h.etf_profile_id, h.ticker, h.isin)
    if matched_p and h.etf_profile_id:
        return matched_p
    if not matched_p and is_fund(q.get("type"), h.ticker):
        try:
            matched_p = await auto_decompose_and_create_profile(db, symbol=h.ticker, name=h.asset_name, isin=h.isin)
        except Exception as e:
            logger.warning(f"Could not auto-decompose {h.ticker}: {e}")
    if not matched_p:
        return None
    try:
        h.etf_profile_id = matched_p.id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    return matched_p


async def _value_holdings(db: Session, holdings: list[PortfolioHolding], quotes: dict[str, Any],
                          fx_rates: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """Valeur EUR de chaque position (repli sur le PRU sans cours connu) et total du portefeuille boursier."""
    total_stocks_eur = 0.0
    valued_holdings = []
    profiles = etf_repo.all_profiles(db)
    for h in holdings:
        q = quotes.get(h.ticker.upper(), {})
        price_eur = q.get("price_eur", 0.0)
        # Aucun cours connu : repli sur le PRU, converti de la devise de la position en EUR
        if price_eur <= 0 and h.buy_price_avg:
            fx = fx_rates.get((h.currency or "EUR").upper())
            price_eur = h.buy_price_avg / fx if fx else 0.0

        profile = await _resolve_profile(db, h, q, profiles)
        val_eur = round(h.quantity * price_eur, 2)
        total_stocks_eur += val_eur
        valued_holdings.append({
            "id": h.id,
            "account_id": h.account_id,
            "ticker": h.ticker,
            "isin": h.isin,
            "name": h.asset_name,
            "quantity": h.quantity,
            "price_eur": price_eur,
            "value_eur": val_eur,
            "etf_profile_id": profile.id if profile else None,
            "quote_type": q.get("type"),
            "is_etf": is_etf_holding(q.get("type"), h.ticker, h.isin, profile),
        })
    return valued_holdings, total_stocks_eur


def _is_direct_stock(vh: dict[str, Any]) -> bool:
    return not vh["etf_profile_id"] and not vh["is_etf"] and not is_crypto(vh.get("quote_type"), vh["ticker"])


def _needs_yahoo(security: Security | None) -> bool:
    """Titre absent, ou sans pays ni secteur et pas interrogé depuis `PROFILE_RETRY` (404 de Yahoo mémorisé)."""
    if security is None:
        return True
    if security.country is not None or security.sector is not None:
        return False
    return security.updated_at < utcnow_naive() - PROFILE_RETRY


async def _enrich_from_yahoo(db: Session, holdings: list[dict[str, Any]], found: dict[str, Security]) -> bool:
    """Interroge Yahoo une fois par titre à compléter ; un titre inconnu de Yahoo est mémorisé (ligne sans pays ni
    secteur) pour ne pas être redemandé à chaque scan. Yahoo injoignable : on s'arrête, rien n'est mémorisé."""
    rows = []
    for vh in holdings:
        if not _needs_yahoo(found.get(vh["isin"])):
            continue
        try:
            profile = await yahoo_finance.fetch_asset_profile(vh["ticker"])
        except yahoo_finance.YahooUnavailable as e:
            logger.warning(f"Profil Yahoo indisponible pour {vh['ticker']}: {e}")
            break
        rows.append({"isin": vh["isin"], "ticker": vh["ticker"].upper().split(".")[0], "exchange": None,
                     "name": vh["name"], "country": (profile or {}).get("country"),
                     "sector": (profile or {}).get("sector"), "source": "yahoo"})
    if not rows:
        return False
    try:
        securities_repo.upsert_many(db, rows)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return False
    return True


def _securities_without_isin(db: Session, holdings: list[dict[str, Any]]) -> dict[str, Security]:
    """Titre d'une position sans ISIN : le seul ISIN de ticker exact et de place compatible (`pick_isin`)."""
    tickers = {vh["ticker"].upper().split(".")[0] for vh in holdings}
    by_ticker: dict[str, list[Security]] = {}
    for sec in securities_repo.by_tickers(db, tickers):
        by_ticker.setdefault(sec.ticker.upper(), []).append(sec)
    result: dict[str, Security] = {}
    for vh in holdings:
        candidates = by_ticker.get(vh["ticker"].upper().split(".")[0], [])
        isin = pick_isin(vh["ticker"], [IsinCandidate(c.isin, c.ticker, c.exchange) for c in candidates])
        match = next((c for c in candidates if c.isin == isin), None)
        if match:
            result[vh["ticker"].upper()] = match
    return result


async def _direct_securities(db: Session, valued_holdings: list[dict[str, Any]]) -> dict[str, Security]:
    """Titres des actions en direct : par ISIN, ou par ticker (clé = ticker de la position) pour une position sans ISIN.

    Yahoo ne sert que les positions avec ISIN (une fois par titre, un seul commit)."""
    direct = [vh for vh in valued_holdings if vh["value_eur"] > 0 and _is_direct_stock(vh)]
    with_isin = [vh for vh in direct if vh.get("isin")]
    found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    if await _enrich_from_yahoo(db, with_isin, found):
        found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    return {**found, **_securities_without_isin(db, [vh for vh in direct if not vh.get("isin")])}


async def _wealth_context(db: Session) -> dict[str, float]:
    """« Ce qu'on a à côté » : épargne, courant, fonds euros des assurances-vie et autres comptes, en EUR.

    Valeurs par `account_values` (source unique, même patrimoine que `patrimoine-allocation`)."""
    totals = {"epargne": 0.0, "courant": 0.0, "fonds_euros": 0.0, "other": 0.0}
    accounts = active_accounts(db)
    values = await account_values(db, accounts)
    for acc in accounts:
        val_acc_eur = values[acc.id].value_eur
        if acc.type == "epargne":
            totals["epargne"] += val_acc_eur
        elif acc.type == "courant":
            totals["courant"] += val_acc_eur
        elif acc.type == "assurance_vie":
            totals["fonds_euros"] += val_acc_eur * ((acc.fonds_euros_pct or 0.0) / 100.0)
        elif acc.type != "investissement":
            totals["other"] += val_acc_eur
    return totals


def _look_through(db: Session, valued_holdings: list[dict[str, Any]], securities: dict[str, Security]) -> LookThrough:
    """Transparence des ETF : profils et lignes de composition chargés une fois pour tout le portefeuille ; un
    synthétique est décomposé par la référence de son indice."""
    profiles = etf_repo.all_profiles(db)
    by_id = {p.id: p for p in profiles}
    held = {
        vh["id"]: by_id.get(vh["etf_profile_id"])
        or match_profile(profiles, vh["ticker"], vh.get("isin"), vh.get("name"))
        for vh in valued_holdings
    }

    def exposed_by(profile: EtfProfile) -> EtfProfile:
        return by_id.get(profile.exposure_profile_id or 0, profile)

    lines = etf_constituents.for_profiles(db, {exposed_by(p).id for p in held.values() if p})

    def exposure_for(profile: EtfProfile) -> Exposure:
        source = exposed_by(profile)
        return Exposure(source, lines.get(source.id, []))

    return look_through(valued_holdings, lambda vh: held[vh["id"]], securities, exposure_for)


async def compute_diversity(db: Session, account_id: int | None) -> dict[str, Any]:
    """Expositions réelles (sociétés, pays, secteurs), doublons, alertes, score HHI et vue patrimoine total."""
    holdings = repo.holdings(db, account_id)
    quotes = await market_quotes.get_market_quotes([h.ticker for h in holdings], db=db)
    market_quotes.persist_fetched_prices(db)
    valued_holdings, total_stocks_eur = await _value_holdings(db, holdings, quotes, await get_exchange_rates("EUR"))
    side = await _wealth_context(db)
    # Patrimoine total : actions valorisées par positions (ou repli) + épargne, liquidités et fonds euros
    total_wealth_eur = round(total_stocks_eur + side["epargne"] + side["courant"] + side["fonds_euros"] + side["other"], 2)

    securities = await _direct_securities(db, valued_holdings)  # commit éventuel avant de charger les profils
    lt = _look_through(db, valued_holdings, securities)
    companies = top_companies(lt.companies, total_stocks_eur, total_wealth_eur)
    countries = exposure_rows(lt.countries, total_stocks_eur, total_wealth_eur)
    sectors = exposure_rows(lt.sectors, total_stocks_eur, total_wealth_eur)
    score = hhi_score([c["total_value_eur"] for c in companies])

    return {
        "score": score,
        "score_label": score_label(score),
        "totals": {
            "stocks_eur": round(total_stocks_eur, 2),
            "direct_eur": round(lt.direct_value_eur, 2),
            "etf_eur": round(lt.etf_value_eur, 2),
            "epargne_eur": round(side["epargne"], 2),
            "courant_eur": round(side["courant"], 2),
            "fonds_euros_eur": round(side["fonds_euros"], 2),
            "other_eur": round(side["other"], 2),
            "wealth_eur": total_wealth_eur,
            "holdings_count": len(valued_holdings),
            "etfs_count": len(lt.etfs),
        },
        "top_underlying_companies": companies[:15],
        "countries": countries,
        "sectors": sectors,
        "alerts": diversity_alerts(companies, countries, sectors),
        "holdings": valued_holdings,
        "etf_compositions": sorted(
            ({**c, "value_eur": round(c["value_eur"], 2)} for c in lt.compositions.values()),
            key=lambda c: c["value_eur"],
            reverse=True,
        ),
    }
