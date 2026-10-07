from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.portfolio import compute_portfolio, uses_positions, xirr
from app.core.holdings import replay_account
from app.db.session import get_db
from app.models.account import Account
from app.schemas.portfolio import PortfolioOverview, PortfolioRead

router = APIRouter()


async def valued_accounts(db: Session, *, history: bool = False) -> list[dict]:
    """Indicateurs de tous les comptes titres actifs valorisés par leurs positions."""
    results = []
    for account in db.query(Account).filter(Account.type == "investissement", Account.active.is_(True)).order_by(Account.id).all():
        if uses_positions(account, await replay_account(db, account.id)):
            results.append(await compute_portfolio(db, account, history=history))
    return results


@router.get("/portfolio", response_model=PortfolioOverview)
async def portfolio_overview(db: Session = Depends(get_db)):
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


@router.get("/portfolio/{account_id}", response_model=PortfolioRead)
async def portfolio_account(account_id: int, db: Session = Depends(get_db)):
    """Valeur calculée (positions × cours + espèces), plus-values, XIRR/TWR, courbe reconstituée et rapprochement."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type not in ("investissement", "assurance_vie"):
        raise HTTPException(status_code=422, detail="Account must be investissement or assurance_vie")
    return PortfolioRead(**await compute_portfolio(db, account))
