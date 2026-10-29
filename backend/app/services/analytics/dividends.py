"""Synthèse des dividendes : totaux nets / bruts en EUR, par mois, par année et par titre (avec rendements)."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.dividends import aggregate_dividends, dividend_tickers, month_keys, position_values
from app.repositories.investissement import holdings as holdings_repo
from app.schemas.dividend import DividendMonth, DividendSummary, DividendTotals, DividendUnlinked, DividendYear
from app.services.investissement.dividends import load_dividends_eur
from app.services.investissement.market.quotes import get_market_quotes


async def compute_dividends(db: Session, account_id: int | None, months: int) -> DividendSummary:
    rows = await load_dividends_eur(db, account_id)
    now = datetime.now()
    agg = aggregate_dividends(rows, now - timedelta(days=365))

    # Positions : coût de revient et valeur actuelle par ticker, pour les rendements
    holdings = holdings_repo.held_positions(db, account_id)
    quotes = await get_market_quotes([h.ticker for h in holdings if h.ticker.upper() in agg.by_ticker], db=db) if holdings else {}
    totals, unlinked = agg.totals, agg.unlinked

    return DividendSummary(
        totals=DividendTotals(
            count=totals.count,
            net_eur=round(totals.net_eur, 2),
            withholding_eur=round(totals.withholding_eur, 2),
            gross_eur=round(totals.net_eur + totals.withholding_eur, 2),
            last_12m_eur=round(totals.last_12m_eur, 2),
        ),
        by_month=[DividendMonth(month=k, net_eur=round(agg.by_month.get(k, 0.0), 2)) for k in month_keys(now, months)],
        by_year=[
            DividendYear(
                year=y,
                count=v["count"],
                net_eur=round(v["net"], 2),
                withholding_eur=round(v["tax"], 2),
                gross_eur=round(v["net"] + v["tax"], 2),
            )
            for y, v in sorted(agg.by_year.items(), reverse=True)
        ],
        by_ticker=dividend_tickers(agg.by_ticker, position_values(holdings, quotes)),
        unlinked=DividendUnlinked(count=unlinked.count, total_eur=round(unlinked.total_eur, 2)),
    )
