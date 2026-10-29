"""Suggestions de titres pour l'inventaire Point Zéro, déduites des libellés des anciennes opérations."""
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.domain.market import extract_asset_clean_name
from app.repositories.investissement import investment_transactions as tx_repo
from app.services.investissement.market.search import search_market_assets


async def suggest_holdings_from_notes(db: Session, account_id: int) -> List[Dict[str, Any]]:
    """
    Intelligently analyzes historical notes in investment_transactions for an account,
    identifies past assets (e.g. Apple, Total, Microsoft, Cisco...) and proposes suggestions
    for the Point Zéro baseline inventory.
    """
    # Aggregate by identified clean asset name
    aggregated: Dict[str, Dict[str, Any]] = {}
    for tx in tx_repo.for_account(db, account_id):
        raw_name = tx.ticker or tx.note or ""
        clean_name = extract_asset_clean_name(raw_name)
        if not clean_name:
            continue

        if clean_name not in aggregated:
            aggregated[clean_name] = {
                "name": clean_name,
                "tx_count": 0,
                "net_amount": 0.0,
                "last_date": tx.date,
            }

        aggregated[clean_name]["tx_count"] += 1
        if tx.type == "versement":
            aggregated[clean_name]["net_amount"] += tx.amount
        elif tx.type == "retrait":
            aggregated[clean_name]["net_amount"] -= tx.amount

        if tx.date > aggregated[clean_name]["last_date"]:
            aggregated[clean_name]["last_date"] = tx.date

    # Resolve tickers for top suggestions
    suggestions: List[Dict[str, Any]] = []
    for asset_name, item in aggregated.items():
        search_res = await search_market_assets(asset_name, db=db)
        best_match = search_res[0] if search_res else None

        symbol = best_match["symbol"] if best_match else asset_name
        official_name = best_match["name"] if best_match else asset_name
        etf_id = best_match.get("etf_profile_id") if best_match else None

        suggestions.append({
            "name": official_name,
            "ticker": symbol,
            "isin": best_match.get("isin") if best_match else None,
            "historical_net_invested": round(item["net_amount"], 2),
            "tx_count": item["tx_count"],
            "etf_profile_id": etf_id,
            "is_etf": bool(etf_id or (best_match and best_match.get("type") == "ETF")),
        })

    # Sort by historical net invested descending
    suggestions.sort(key=lambda x: x["historical_net_invested"], reverse=True)
    return suggestions
