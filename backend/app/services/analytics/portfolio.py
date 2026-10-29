"""Portefeuille titres : comptes valorisés par positions et synthèse (valeur, plus-values, dividendes, XIRR)."""
from sqlalchemy.orm import Session

from app.services.holdings.replay import replay_account
from app.domain.performance import xirr
from app.domain.portfolio import uses_positions
from app.services.portfolio import compute_portfolio
from app.repositories.analytics import investments as repo
from app.schemas.portfolio import PortfolioOverview, PortfolioRead


async def valued_accounts(db: Session, *, history: bool = False) -> list[dict]:
    """Indicateurs de tous les comptes titres actifs valorisés par leurs positions."""
    results = []
    for account in repo.securities_accounts(db):
        if uses_positions(account, await replay_account(db, account.id)):
            results.append(await compute_portfolio(db, account, history=history))
    return results


async def portfolio_overview(db: Session) -> PortfolioOverview:
    """Somme des comptes titres valorisés par positions : valeur, plus-values latente/réalisée, dividendes, XIRR."""
    accounts = await valued_accounts(db)
    net_invested = sum(a["net_invested_eur"] for a in accounts)
    value = sum(a["value_eur"] for a in accounts)
    unrealized = [a["unrealized_eur"] for a in accounts if a["unrealized_eur"] is not None]

    years: dict[int, dict] = {}
    for a in accounts:
        for y in a["realized_by_year"]:
            agg = years.setdefault(y["year"], {"year": y["year"], "realized_eur": 0.0, "proceeds_eur": 0.0, "sales": 0})
            agg["realized_eur"] += y["realized_eur"]
            agg["proceeds_eur"] += y["proceeds_eur"]
            agg["sales"] += y["sales"]

    flows = [flow for a in accounts for flow in a["_xirr_flows_eur"] if flow[0] is not None]
    # Valeurs finales : un flux positif par compte à la même date, on les additionne par jour
    merged: dict = {}
    for day, amount in flows:
        merged[day] = merged.get(day, 0.0) + amount
    rate = xirr(sorted(merged.items())) if accounts else None

    return PortfolioOverview(
        accounts=[PortfolioRead(**a) for a in accounts],
        value_eur=round(value, 2),
        net_invested_eur=round(net_invested, 2),
        gain_eur=round(value - net_invested, 2),
        performance_pct=round((value - net_invested) / net_invested * 100.0, 2) if net_invested > 0 else None,
        xirr_pct=round(rate * 100.0, 2) if rate is not None else None,
        unrealized_eur=round(sum(unrealized), 2) if unrealized else None,
        realized_eur=round(sum(a["realized_eur"] for a in accounts), 2),
        realized_by_year=[
            {**y, "realized_eur": round(y["realized_eur"], 2), "proceeds_eur": round(y["proceeds_eur"], 2)}
            for y in sorted(years.values(), key=lambda e: e["year"], reverse=True)
        ],
        dividends_eur=round(sum(a["dividends_eur"] for a in accounts), 2),
        dividends_12m_eur=round(sum(a["dividends_12m_eur"] for a in accounts), 2),
        fees_eur=round(sum(a["fees_eur"] for a in accounts), 2),
    )
