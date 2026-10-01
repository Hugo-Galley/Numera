import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.currency import get_exchange_rates
from app.core.market_data import get_market_quotes, _match_etf_profile
from app.db.session import get_db
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction

logger = get_logger(__name__)

router = APIRouter(tags=["diversity-scanner"])


def _normalize_company_key(ticker: Optional[str], name: Optional[str]) -> str:
    import re
    if ticker:
        clean_t = ticker.upper().split(".")[0].strip()
        if len(clean_t) >= 2:
            return f"TICKER:{clean_t}"
    if name:
        clean_n = re.sub(r'\b(inc|sa|se|plc|corp|corporation|group|ltd|ag|nv|spa)\b\.?', '', name, flags=re.IGNORECASE).strip().lower()
        clean_n = re.sub(r'[^a-z0-9]', '', clean_n)
        if clean_n:
            return f"NAME:{clean_n}"
    return f"RAW:{ticker or name or 'unknown'}"


def _calculate_hhi_score(weights: List[float]) -> float:
    """
    Computes a 0-100 score based on Herfindahl-Hirschman Index (HHI).
    HHI ranges from ~0 (infinite diversity) to 10,000 (100% single asset).
    Score:
      HHI <= 1000 -> 90 - 100
      HHI 1000 - 1800 -> 75 - 89
      HHI 1800 - 2500 -> 55 - 74
      HHI > 2500 -> 10 - 54
    """
    if not weights or sum(weights) <= 0:
        return 50.0

    total = sum(weights)
    hhi = sum(((w / total) * 100.0) ** 2 for w in weights)

    # Invert HHI to a 0-100 score
    if hhi <= 1000:
        score = 90.0 + (1000.0 - hhi) / 1000.0 * 10.0
    elif hhi <= 1800:
        score = 75.0 + (1800.0 - hhi) / 800.0 * 15.0
    elif hhi <= 2500:
        score = 55.0 + (2500.0 - hhi) / 700.0 * 20.0
    elif hhi <= 5000:
        score = 30.0 + (5000.0 - hhi) / 2500.0 * 25.0
    else:
        score = max(10.0, 30.0 * (10000.0 - hhi) / 5000.0)

    return round(min(100.0, max(5.0, score)), 1)


@router.get("/analytics/diversity-scanner")
async def diversity_scanner(
    account_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Consolidated Diversity & ETF Look-Through Scanner.
    Computes true underlying company exposures, country/sector breakdown,
    redundancy & overlap detection, diversity score, and dual-view (Stocks vs Total Wealth).
    """
    # 1. Fetch investment holdings
    holdings_q = db.query(PortfolioHolding)
    if account_id is not None:
        holdings_q = holdings_q.filter(PortfolioHolding.account_id == account_id)
    holdings = holdings_q.all()

    # Pre-fetch live quotes
    symbols = [h.ticker for h in holdings]
    quotes = await get_market_quotes(symbols)

    # 2. Value each holding in EUR
    total_stocks_eur = 0.0
    valued_holdings = []
    for h in holdings:
        q = quotes.get(h.ticker.upper(), {})
        price_eur = q.get("price_eur", 0.0)
        # Fallback to buy price if market price is 0
        if price_eur <= 0 and h.buy_price_avg:
            price_eur = h.buy_price_avg

        profile_id = h.etf_profile_id
        if not profile_id:
            matched_p = _match_etf_profile(db, symbol=h.ticker, isin=h.isin, name=h.asset_name)
            if not matched_p:
                norm_upper = f"{h.ticker} {h.asset_name or ''}".upper()
                if (
                    h.ticker.upper().startswith("0P")
                    or q.get("type") in ("ETF", "MUTUALFUND")
                    or any(k in norm_upper for k in ["ETF", "FCP", "SICAV", "TRACKER", "INDEX", "FONDS", "FUND"])
                ):
                    try:
                        from app.core.etf_analyzer import auto_decompose_and_create_profile
                        matched_p = await auto_decompose_and_create_profile(db, symbol=h.ticker, name=h.asset_name, isin=h.isin)
                    except Exception as e:
                        logger.warning(f"Could not auto-decompose {h.ticker}: {e}")

            if matched_p:
                profile_id = matched_p.id
                try:
                    h.etf_profile_id = matched_p.id
                    db.commit()
                except Exception:
                    db.rollback()

        is_etf = bool(profile_id or q.get("type") in ("ETF", "MUTUALFUND"))

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
            "is_etf": is_etf,
        })

    # 3. Calculate "Ce qu'on a à côté" (Total Wealth context)
    all_accounts = db.query(Account).filter(Account.active.is_(True)).all()
    rates = await get_exchange_rates("EUR")

    total_epargne_eur = 0.0
    total_courant_eur = 0.0
    total_fonds_euros_eur = 0.0
    total_other_eur = 0.0

    for acc in all_accounts:
        # Get latest snapshot or last running balance
        latest_snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == acc.id)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        val_raw = float(latest_snap.current_value) if latest_snap else 0.0
        if not latest_snap:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                val_raw = float(last_tx.running_balance)

        val_acc_eur = val_raw / rates.get(acc.currency, 1.0) if val_raw > 0 else 0.0

        if acc.type == "epargne":
            total_epargne_eur += val_acc_eur
        elif acc.type == "courant":
            total_courant_eur += val_acc_eur
        elif acc.type == "assurance_vie":
            fe_pct = (acc.fonds_euros_pct or 0.0) / 100.0
            total_fonds_euros_eur += val_acc_eur * fe_pct
        elif acc.type != "investissement":
            total_other_eur += val_acc_eur

    # Total wealth includes stocks valued dynamically via holdings (or fallback) + safe assets + cash
    total_wealth_eur = round(total_stocks_eur + total_epargne_eur + total_courant_eur + total_fonds_euros_eur + total_other_eur, 2)

    # 4. Look-Through Aggregation
    underlying_companies: Dict[str, Dict[str, Any]] = {}
    underlying_countries: Dict[str, float] = {}
    underlying_sectors: Dict[str, float] = {}
    etfs_breakdown: List[Dict[str, Any]] = []

    # Cache ETF profiles
    profiles_by_id = {p.id: p for p in db.query(EtfProfile).all()}

    for vh in valued_holdings:
        vh_val = vh["value_eur"]
        if vh_val <= 0:
            continue

        etf_profile = profiles_by_id.get(vh["etf_profile_id"]) if vh["etf_profile_id"] else None
        if not etf_profile:
            etf_profile = _match_etf_profile(db, symbol=vh["ticker"], isin=vh.get("isin"), name=vh.get("name"))

        if etf_profile:
            # It's an ETF -> decompose into underlying assets
            etfs_breakdown.append({
                "ticker": vh["ticker"],
                "name": vh["name"],
                "value_eur": vh_val,
                "profile_name": etf_profile.name,
            })

            # Countries
            try:
                c_dict = json.loads(etf_profile.countries)
                for country, weight in c_dict.items():
                    val = vh_val * (float(weight) / 100.0)
                    underlying_countries[country] = underlying_countries.get(country, 0.0) + val
            except Exception:
                underlying_countries["Monde"] = underlying_countries.get("Monde", 0.0) + vh_val

            # Sectors
            try:
                s_dict = json.loads(etf_profile.sectors)
                for sector, weight in s_dict.items():
                    val = vh_val * (float(weight) / 100.0)
                    underlying_sectors[sector] = underlying_sectors.get(sector, 0.0) + val
            except Exception:
                underlying_sectors["Diversifié"] = underlying_sectors.get("Diversifié", 0.0) + vh_val

            # Top holdings look-through
            try:
                h_list = json.loads(etf_profile.top_holdings)
                for h_item in h_list:
                    h_name = h_item["name"]
                    h_ticker = h_item.get("ticker")
                    h_weight = float(h_item.get("weight", 0.0))
                    h_val = vh_val * (h_weight / 100.0)
                    key = _normalize_company_key(h_ticker, h_name)

                    if key not in underlying_companies:
                        underlying_companies[key] = {
                            "name": h_name,
                            "ticker": h_ticker,
                            "direct_value_eur": 0.0,
                            "indirect_value_eur": 0.0,
                            "sources": [],
                        }

                    underlying_companies[key]["indirect_value_eur"] += h_val
                    underlying_companies[key]["sources"].append({
                        "source": vh["ticker"],
                        "pct_in_source": round(h_weight, 2),
                        "value_eur": round(h_val, 2),
                    })
            except Exception as e:
                logger.warning(f"Error parsing ETF holdings for {etf_profile.name}: {e}")

        else:
            # Direct stock / single security
            direct_name = vh["name"]
            direct_ticker = vh.get("ticker")
            key = _normalize_company_key(direct_ticker, direct_name)
            if key not in underlying_companies:
                underlying_companies[key] = {
                    "name": direct_name,
                    "ticker": direct_ticker,
                    "direct_value_eur": 0.0,
                    "indirect_value_eur": 0.0,
                    "sources": [],
                }

            underlying_companies[key]["direct_value_eur"] += vh_val
            underlying_companies[key]["sources"].append({
                "source": "En direct",
                "pct_in_source": 100.0,
                "value_eur": round(vh_val, 2),
            })

            # Country & sector defaults for direct stocks
            underlying_countries["Autres"] = underlying_countries.get("Autres", 0.0) + vh_val
            underlying_sectors["Actions directes"] = underlying_sectors.get("Actions directes", 0.0) + vh_val

    # 5. Format Top Companies & Exposures
    top_companies_list = []
    for comp in underlying_companies.values():
        total_comp_eur = round(comp["direct_value_eur"] + comp["indirect_value_eur"], 2)
        pct_stocks = round((total_comp_eur / total_stocks_eur * 100.0), 2) if total_stocks_eur > 0 else 0.0
        pct_wealth = round((total_comp_eur / total_wealth_eur * 100.0), 2) if total_wealth_eur > 0 else 0.0

        top_companies_list.append({
            "name": comp["name"],
            "ticker": comp["ticker"],
            "direct_value_eur": round(comp["direct_value_eur"], 2),
            "indirect_value_eur": round(comp["indirect_value_eur"], 2),
            "total_value_eur": total_comp_eur,
            "pct_stocks": pct_stocks,
            "pct_total_wealth": pct_wealth,
            "sources": comp["sources"],
            "has_overlap": len(comp["sources"]) > 1,
        })

    top_companies_list.sort(key=lambda c: c["total_value_eur"], reverse=True)

    # 6. Format Countries and Sectors
    formatted_countries = []
    for c_name, c_val in underlying_countries.items():
        pct_s = round((c_val / total_stocks_eur * 100.0), 2) if total_stocks_eur > 0 else 0.0
        pct_w = round((c_val / total_wealth_eur * 100.0), 2) if total_wealth_eur > 0 else 0.0
        formatted_countries.append({
            "name": c_name,
            "value_eur": round(c_val, 2),
            "percentage_stocks": pct_s,
            "percentage_total_wealth": pct_w,
        })
    formatted_countries.sort(key=lambda x: x["value_eur"], reverse=True)

    formatted_sectors = []
    for s_name, s_val in underlying_sectors.items():
        pct_s = round((s_val / total_stocks_eur * 100.0), 2) if total_stocks_eur > 0 else 0.0
        pct_w = round((s_val / total_wealth_eur * 100.0), 2) if total_wealth_eur > 0 else 0.0
        formatted_sectors.append({
            "name": s_name,
            "value_eur": round(s_val, 2),
            "percentage_stocks": pct_s,
            "percentage_total_wealth": pct_w,
        })
    formatted_sectors.sort(key=lambda x: x["value_eur"], reverse=True)

    # 7. Redundancy & Alerts Detection
    alerts = []

    # Alert: Overconcentrated Company
    for comp in top_companies_list:
        if comp["pct_stocks"] >= 20.0:
            alerts.append({
                "type": "danger",
                "category": "company",
                "title": f"Concentration critique sur {comp['name']}",
                "message": f"{comp['name']} pèse {comp['pct_stocks']}% de votre portefeuille boursier ({comp['pct_total_wealth']}% du patrimoine total). Ce niveau de concentration sur un seul titre présente un risque spécifique élevé.",
                "item_name": comp["name"],
                "value_pct": comp["pct_stocks"],
            })
        elif comp["pct_stocks"] >= 10.0:
            alerts.append({
                "type": "warning",
                "category": "company",
                "title": f"Forte exposition sur {comp['name']}",
                "message": f"{comp['name']} représente {comp['pct_stocks']}% de vos actions/ETFs ({comp['pct_total_wealth']}% du patrimoine total).",
                "item_name": comp["name"],
                "value_pct": comp["pct_stocks"],
            })

    # Alert: Overlaps (Doublons)
    overlap_companies = [c for c in top_companies_list if c["has_overlap"]]
    if overlap_companies:
        overlap_names = [c["name"] for c in overlap_companies[:3]]
        sources_str = ", ".join(overlap_names)
        alerts.append({
            "type": "info",
            "category": "overlap",
            "title": f"Doublons d'exposition détectés ({len(overlap_companies)} titres)",
            "message": f"Vous détenez des titres simultanément en direct et/ou à travers plusieurs ETFs (notamment {sources_str}). Leur pondération réelle s'additionne discrètement.",
            "item_name": sources_str,
            "value_pct": sum(c["pct_stocks"] for c in overlap_companies[:3]),
        })

    # Alert: Geography concentration
    for country in formatted_countries:
        if country["name"] in ("USA", "États-Unis") and country["percentage_stocks"] >= 65.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": f"Forte prépondérance américaine ({country['percentage_stocks']}%)",
                "message": f"{country['percentage_stocks']}% de votre exposition boursière est concentrée sur les États-Unis. Sensibilité accrue au dollar et aux marchés US.",
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })
        elif country["name"] in ("FRA", "France") and country["percentage_stocks"] >= 35.0:
            alerts.append({
                "type": "warning",
                "category": "country",
                "title": f"Biais domestique français ({country['percentage_stocks']}%)",
                "message": f"Votre portefeuille actions alloue {country['percentage_stocks']}% à la France. Pensez à diversifier géographiquement.",
                "item_name": country["name"],
                "value_pct": country["percentage_stocks"],
            })

    # Alert: Sector concentration
    for sector in formatted_sectors:
        if sector["percentage_stocks"] >= 30.0:
            alerts.append({
                "type": "warning",
                "category": "sector",
                "title": f"Sur-exposition sectorielle : {sector['name']} ({sector['percentage_stocks']}%)",
                "message": f"Le secteur {sector['name']} domine {sector['percentage_stocks']}% de vos investissements en actions.",
                "item_name": sector["name"],
                "value_pct": sector["percentage_stocks"],
            })

    # 8. Diversity Score (HHI)
    company_weights = [c["total_value_eur"] for c in top_companies_list]
    diversity_score = _calculate_hhi_score(company_weights)

    score_label = "Excellente diversification"
    if diversity_score < 40:
        score_label = "Concentration critique"
    elif diversity_score < 60:
        score_label = "Concentration modérée"
    elif diversity_score < 80:
        score_label = "Bonne diversification globale"

    return {
        "score": diversity_score,
        "score_label": score_label,
        "totals": {
            "stocks_eur": round(total_stocks_eur, 2),
            "epargne_eur": round(total_epargne_eur, 2),
            "courant_eur": round(total_courant_eur, 2),
            "fonds_euros_eur": round(total_fonds_euros_eur, 2),
            "other_eur": round(total_other_eur, 2),
            "wealth_eur": total_wealth_eur,
            "holdings_count": len(valued_holdings),
            "etfs_count": len(etfs_breakdown),
        },
        "top_underlying_companies": top_companies_list[:15],
        "countries": formatted_countries,
        "sectors": formatted_sectors,
        "alerts": alerts,
        "holdings": valued_holdings,
    }
