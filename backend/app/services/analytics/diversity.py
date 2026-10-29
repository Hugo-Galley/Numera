"""Scanner de diversification : expositions réelles par transparence des ETF, doublons, score et alertes,
rapportées au portefeuille boursier et au patrimoine total."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.diversity import diversity_alerts, exposure_rows, hhi_score, look_through, score_label, top_companies
from app.integrations.currency import get_exchange_rates
from app.models.portfolio_holding import PortfolioHolding
from app.repositories import etf_profiles as etf_repo
from app.repositories.analytics import diversity as repo
from app.services.etf_profiles import auto_decompose_and_create_profile
from app.services.market import quotes as market_quotes
from app.services.market.search import match_etf_profile

logger = get_logger(__name__)

FUND_KEYWORDS = ["ETF", "FCP", "SICAV", "TRACKER", "INDEX", "FONDS", "FUND"]


async def _resolve_profile_id(db: Session, h: PortfolioHolding, q: dict) -> Optional[int]:
    """Profil ETF de la position : rattaché, retrouvé, ou créé depuis Yahoo pour un fonds inconnu (rattachement commité)."""
    if h.etf_profile_id:
        return h.etf_profile_id
    matched_p = match_etf_profile(db, symbol=h.ticker, isin=h.isin, name=h.asset_name)
    if not matched_p:
        norm_upper = f"{h.ticker} {h.asset_name or ''}".upper()
        if (
            h.ticker.upper().startswith("0P")
            or q.get("type") in ("ETF", "MUTUALFUND")
            or any(k in norm_upper for k in FUND_KEYWORDS)
        ):
            try:
                matched_p = await auto_decompose_and_create_profile(db, symbol=h.ticker, name=h.asset_name, isin=h.isin)
            except Exception as e:
                logger.warning(f"Could not auto-decompose {h.ticker}: {e}")
    if not matched_p:
        return None
    try:
        h.etf_profile_id = matched_p.id
        db.commit()
    except Exception:
        db.rollback()
    return matched_p.id


async def _value_holdings(db: Session, holdings: List[PortfolioHolding], quotes: dict,
                          fx_rates: dict) -> tuple[List[Dict[str, Any]], float]:
    """Valeur EUR de chaque position (repli sur le PRU sans cours connu) et total du portefeuille boursier."""
    total_stocks_eur = 0.0
    valued_holdings = []
    for h in holdings:
        q = quotes.get(h.ticker.upper(), {})
        price_eur = q.get("price_eur", 0.0)
        # Aucun cours connu : repli sur le PRU, converti de la devise de la position en EUR
        if price_eur <= 0 and h.buy_price_avg:
            fx = fx_rates.get((h.currency or "EUR").upper())
            price_eur = h.buy_price_avg / fx if fx else 0.0

        profile_id = await _resolve_profile_id(db, h, q)
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
            "etf_profile_id": profile_id,
            "is_etf": bool(profile_id or q.get("type") in ("ETF", "MUTUALFUND")),
        })
    return valued_holdings, total_stocks_eur


def _wealth_context(db: Session, rates: dict) -> Dict[str, float]:
    """« Ce qu'on a à côté » : épargne, courant, fonds euros des assurances-vie et autres comptes, en EUR."""
    totals = {"epargne": 0.0, "courant": 0.0, "fonds_euros": 0.0, "other": 0.0}
    for acc in repo.active_accounts(db):
        # Dernier relevé, sinon solde courant de la dernière transaction
        latest_snap = repo.latest_snapshot(db, acc.id)
        val_raw = float(latest_snap.current_value) if latest_snap else 0.0
        if not latest_snap:
            last_tx = repo.last_transaction(db, acc.id)
            if last_tx:
                val_raw = float(last_tx.running_balance)

        val_acc_eur = val_raw / rates.get(acc.currency, 1.0) if val_raw > 0 else 0.0
        if acc.type == "epargne":
            totals["epargne"] += val_acc_eur
        elif acc.type == "courant":
            totals["courant"] += val_acc_eur
        elif acc.type == "assurance_vie":
            totals["fonds_euros"] += val_acc_eur * ((acc.fonds_euros_pct or 0.0) / 100.0)
        elif acc.type != "investissement":
            totals["other"] += val_acc_eur
    return totals


async def compute_diversity(db: Session, account_id: Optional[int]) -> Dict[str, Any]:
    """Expositions réelles (sociétés, pays, secteurs), doublons, alertes, score HHI et vue patrimoine total."""
    holdings = repo.holdings(db, account_id)
    quotes = await market_quotes.get_market_quotes([h.ticker for h in holdings], db=db)
    valued_holdings, total_stocks_eur = await _value_holdings(db, holdings, quotes, await get_exchange_rates("EUR"))
    side = _wealth_context(db, await get_exchange_rates("EUR"))
    # Patrimoine total : actions valorisées par positions (ou repli) + épargne, liquidités et fonds euros
    total_wealth_eur = round(total_stocks_eur + side["epargne"] + side["courant"] + side["fonds_euros"] + side["other"], 2)

    profiles_by_id = {p.id: p for p in etf_repo.all_profiles(db)}

    def profile_for(vh: Dict[str, Any]):
        etf_profile = profiles_by_id.get(vh["etf_profile_id"]) if vh["etf_profile_id"] else None
        return etf_profile or match_etf_profile(db, symbol=vh["ticker"], isin=vh.get("isin"), name=vh.get("name"))

    lt = look_through(valued_holdings, profile_for)
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
