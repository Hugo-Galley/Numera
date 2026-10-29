"""Positions enrichies pour l'affichage : cours, valeur, plus-value, dividendes reçus et rendement total."""
from sqlalchemy.orm import Session

from app.domain.dividends import HoldingDividends, summarize_by_holding
from app.domain.holdings import holding_returns
from app.integrations.currency import get_exchange_rates
from app.models.portfolio_holding import PortfolioHolding
from app.schemas.holding import PortfolioHoldingRead
from app.services.dividends import load_dividends_eur
from app.services.market.quotes import get_market_quotes


def enrich_holding(holding: PortfolioHolding, quotes: dict, rates: dict, divs: HoldingDividends | None = None) -> PortfolioHoldingRead:
    sym = holding.ticker.upper().strip()
    quote = quotes.get(sym, {})
    price = quote.get("price", 0.0) or 0.0
    price_eur = quote.get("price_eur", 0.0) or 0.0
    divs = divs or HoldingDividends()
    figures = holding_returns(holding.quantity, price_eur, holding.cost_basis_eur, holding.buy_price_avg,
                              rates.get((holding.currency or "EUR").upper()), divs.total_eur)
    value_eur, invested_eur = figures["value_eur"], figures["invested_eur"]

    return PortfolioHoldingRead(
        id=holding.id,
        account_id=holding.account_id,
        ticker=holding.ticker,
        isin=holding.isin,
        asset_name=holding.asset_name,
        quantity=holding.quantity,
        buy_price_avg=holding.buy_price_avg,
        currency=holding.currency,
        etf_profile_id=holding.etf_profile_id,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        current_price=round(price, 4) if price > 0 else None,
        current_price_eur=round(price_eur, 4) if price_eur > 0 else None,
        quote_currency=quote.get("currency") if price > 0 else None,
        price_date=quote.get("price_date") if price > 0 else None,
        price_stale=bool(quote.get("stale", price <= 0)),
        current_value_eur=round(value_eur, 2) if value_eur > 0 else None,
        total_invested_eur=round(invested_eur, 2) if invested_eur is not None else None,
        gain_eur=figures["gain_eur"],
        gain_pct=figures["gain_pct"],
        is_etf=bool(holding.etf_profile_id or quote.get("type") == "ETF"),
        pays_dividends=holding.pays_dividends,
        dividends_received_eur=round(divs.total_eur, 2),
        dividends_12m_eur=round(divs.last_12m_eur, 2),
        last_dividend_date=divs.last_date.isoformat() if divs.last_date else None,
        total_return_eur=figures["total_return_eur"],
        total_return_pct=figures["total_return_pct"],
    )


async def enrich_all(db: Session, holdings: list[PortfolioHolding]) -> list[PortfolioHoldingRead]:
    quotes = await get_market_quotes([h.ticker for h in holdings], db=db)
    rates = await get_exchange_rates("EUR")
    dividends = summarize_by_holding(await load_dividends_eur(db))
    return [enrich_holding(h, quotes, rates, dividends.get((h.account_id, h.ticker.upper()))) for h in holdings]
