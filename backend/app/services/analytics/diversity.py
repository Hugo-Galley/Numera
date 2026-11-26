"""Scanner de diversification : expositions réelles par transparence des ETF, doublons, score et alertes,
rapportées au portefeuille boursier et au patrimoine total."""
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.diversity import diversity_alerts, exposure_rows, hhi_score, look_through, score_label, top_companies
from app.domain.holdings import holding_profile, is_crypto, is_etf_holding, is_fund
from app.integrations import yahoo_finance
from app.integrations.currency import get_exchange_rates
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.security import Security
from app.repositories.analytics import diversity as repo
from app.repositories.comptes.balances import active_accounts
from app.repositories.investissement import etf_profiles as etf_repo
from app.repositories.investissement import securities as securities_repo
from app.services.comptes.wealth import account_values
from app.services.investissement.etf_profiles import auto_decompose_and_create_profile
from app.services.investissement.market import quotes as market_quotes
from app.services.investissement.market.search import match_etf_profile

logger = get_logger(__name__)


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


def _lacks_profile(security: Security | None) -> bool:
    return security is None or (security.country is None and security.sector is None)


async def _direct_securities(db: Session, valued_holdings: list[dict[str, Any]]) -> dict[str, Security]:
    """Titres des actions en direct, par ISIN (ou par ticker pour une position sans ISIN, si un seul titre le porte).

    Un titre avec ISIN absent du référentiel est demandé une fois à Yahoo (`source="yahoo"`, un seul commit) ;
    Yahoo injoignable : on s'en passe et le pays et le secteur restent « Non renseigné »."""
    direct = [vh for vh in valued_holdings if vh["value_eur"] > 0 and _is_direct_stock(vh)]
    with_isin = [vh for vh in direct if vh.get("isin")]
    found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    rows = []
    for vh in with_isin:
        if vh["isin"] in found and not _lacks_profile(found[vh["isin"]]):
            continue
        try:
            profile = await yahoo_finance.fetch_asset_profile(vh["ticker"])
        except yahoo_finance.YahooUnavailable as e:
            logger.warning(f"Profil Yahoo indisponible pour {vh['ticker']}: {e}")
            break
        if profile:
            rows.append({"isin": vh["isin"], "ticker": vh["ticker"].upper().split(".")[0], "exchange": None,
                         "name": vh["name"], "country": profile["country"], "sector": profile["sector"], "source": "yahoo"})
    if rows:
        try:
            securities_repo.upsert_many(db, rows)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        else:
            found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    result = dict(found)
    no_isin = [vh["ticker"].upper() for vh in direct if not vh.get("isin")]
    by_ticker: dict[str, list[Security]] = {}
    for s in securities_repo.by_tickers(db, {t.split(".")[0] for t in no_isin}):
        by_ticker.setdefault(s.ticker, []).append(s)
    for ticker in no_isin:
        matches = by_ticker.get(ticker.split(".")[0], [])
        if len(matches) == 1:
            result[ticker] = matches[0]
    return result


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


async def compute_diversity(db: Session, account_id: int | None) -> dict[str, Any]:
    """Expositions réelles (sociétés, pays, secteurs), doublons, alertes, score HHI et vue patrimoine total."""
    holdings = repo.holdings(db, account_id)
    quotes = await market_quotes.get_market_quotes([h.ticker for h in holdings], db=db)
    market_quotes.persist_fetched_prices(db)
    valued_holdings, total_stocks_eur = await _value_holdings(db, holdings, quotes, await get_exchange_rates("EUR"))
    side = await _wealth_context(db)
    # Patrimoine total : actions valorisées par positions (ou repli) + épargne, liquidités et fonds euros
    total_wealth_eur = round(total_stocks_eur + side["epargne"] + side["courant"] + side["fonds_euros"] + side["other"], 2)

    profiles_by_id = {p.id: p for p in etf_repo.all_profiles(db)}

    def profile_for(vh: dict[str, Any]) -> EtfProfile | None:
        etf_profile = profiles_by_id.get(vh["etf_profile_id"]) if vh["etf_profile_id"] else None
        return etf_profile or match_etf_profile(db, symbol=vh["ticker"], isin=vh.get("isin"), name=vh.get("name"))

    lt = look_through(valued_holdings, profile_for, await _direct_securities(db, valued_holdings))
    companies = top_companies(lt.companies, total_stocks_eur, total_wealth_eur)
    countries = exposure_rows(lt.countries, total_stocks_eur, total_wealth_eur)
    sectors = exposure_rows(lt.sectors, total_stocks_eur, total_wealth_eur)
    score = hhi_score([c["total_value_eur"] for c in companies])

    return {
        "score": score,
        "score_label": score_label(score),
        "totals": {
            "stocks_eur": round(total_stocks_eur, 2),
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
