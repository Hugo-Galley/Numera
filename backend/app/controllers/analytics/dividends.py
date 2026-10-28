from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dividends import load_dividends_eur
from app.core.market_data import get_market_quotes
from app.db.session import get_db
from app.models.portfolio_holding import PortfolioHolding
from app.schemas.dividend import (
    DividendMonth,
    DividendSummary,
    DividendTicker,
    DividendTotals,
    DividendUnlinked,
    DividendYear,
)

router = APIRouter()


def _month_keys(end: datetime, months: int) -> list[str]:
    keys, year, month = [], end.year, end.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(keys))


@router.get("/dividends", response_model=DividendSummary)
async def get_dividends(
    account_id: int | None = Query(default=None),
    months: int = Query(default=24, ge=1, le=120),
    db: Session = Depends(get_db),
):
    """Dividendes nets / bruts en EUR : totaux, par mois, par année et par titre (avec rendements)."""
    rows = await load_dividends_eur(db, account_id)
    now = datetime.now()
    since = now - timedelta(days=365)

    totals = DividendTotals()
    unlinked = DividendUnlinked()
    by_month: dict[str, float] = defaultdict(float)
    by_year: dict[int, dict] = defaultdict(lambda: {"count": 0, "net": 0.0, "tax": 0.0})
    by_ticker: dict[str, dict] = {}

    for row in rows:
        tx = row.tx
        totals.count += 1
        totals.net_eur += row.net_eur
        totals.withholding_eur += row.tax_eur
        if tx.date >= since:
            totals.last_12m_eur += row.net_eur
        by_month[tx.date.strftime("%Y-%m")] += row.net_eur
        year = by_year[tx.date.year]
        year["count"] += 1
        year["net"] += row.net_eur
        year["tax"] += row.tax_eur

        if not tx.ticker:
            unlinked.count += 1
            unlinked.total_eur += row.net_eur
            continue
        item = by_ticker.setdefault(
            tx.ticker.upper(), {"count": 0, "total": 0.0, "last12": 0.0, "last_date": None, "name": tx.note or tx.ticker}
        )
        item["count"] += 1
        item["total"] += row.net_eur
        if tx.date >= since:
            item["last12"] += row.net_eur
        if item["last_date"] is None or tx.date > item["last_date"]:
            item["last_date"] = tx.date

    # Positions : coût de revient et valeur actuelle par ticker, pour les rendements
    holdings_q = db.query(PortfolioHolding).filter(PortfolioHolding.quantity > 0)
    if account_id is not None:
        holdings_q = holdings_q.filter(PortfolioHolding.account_id == account_id)
    holdings = holdings_q.all()
    quotes = await get_market_quotes([h.ticker for h in holdings if h.ticker.upper() in by_ticker], db=db) if holdings else {}
    positions: dict[str, dict] = {}
    for h in holdings:
        pos = positions.setdefault(h.ticker.upper(), {"name": h.asset_name, "cost": 0.0, "has_cost": True, "value": 0.0, "has_value": True})
        if h.cost_basis_eur:
            pos["cost"] += h.cost_basis_eur
        else:
            pos["has_cost"] = False
        price_eur = (quotes.get(h.ticker.upper()) or {}).get("price_eur") or 0.0
        if price_eur > 0:
            pos["value"] += h.quantity * price_eur
        else:
            pos["has_value"] = False

    tickers: list[DividendTicker] = []
    for ticker, item in by_ticker.items():
        pos = positions.get(ticker)
        tickers.append(
            DividendTicker(
                ticker=ticker,
                asset_name=pos["name"] if pos else item["name"],
                count=item["count"],
                total_eur=round(item["total"], 2),
                last_12m_eur=round(item["last12"], 2),
                last_date=item["last_date"].date().isoformat() if item["last_date"] else None,
                yield_on_cost_pct=round(item["last12"] / pos["cost"] * 100, 2) if pos and pos["has_cost"] and pos["cost"] > 0 else None,
                current_yield_pct=round(item["last12"] / pos["value"] * 100, 2) if pos and pos["has_value"] and pos["value"] > 0 else None,
            )
        )
    tickers.sort(key=lambda t: t.total_eur, reverse=True)

    return DividendSummary(
        totals=DividendTotals(
            count=totals.count,
            net_eur=round(totals.net_eur, 2),
            withholding_eur=round(totals.withholding_eur, 2),
            gross_eur=round(totals.net_eur + totals.withholding_eur, 2),
            last_12m_eur=round(totals.last_12m_eur, 2),
        ),
        by_month=[DividendMonth(month=k, net_eur=round(by_month.get(k, 0.0), 2)) for k in _month_keys(now, months)],
        by_year=[
            DividendYear(
                year=y,
                count=v["count"],
                net_eur=round(v["net"], 2),
                withholding_eur=round(v["tax"], 2),
                gross_eur=round(v["net"] + v["tax"], 2),
            )
            for y, v in sorted(by_year.items(), reverse=True)
        ],
        by_ticker=tickers,
        unlinked=DividendUnlinked(count=unlinked.count, total_eur=round(unlinked.total_eur, 2)),
    )
