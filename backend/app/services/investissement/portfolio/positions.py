"""Positions actuelles valorisées au dernier cours : lignes, valeur, plus-value latente et effet de change."""
from dataclasses import dataclass, field

from app.domain.holdings import Replay
from app.models.portfolio_holding import PortfolioHolding
from app.services.investissement.portfolio.books import FxBook


@dataclass
class PositionsValuation:
    lines: list[dict] = field(default_factory=list)
    value_eur: float = 0.0
    unrealized_eur: float = 0.0
    unrealized_cost_eur: float = 0.0
    fx_effect_eur: float = 0.0
    unpriced: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)


def _line(ticker: str, pos, meta: PortfolioHolding | None, quote: dict, pru, cost_eur, priced: bool, price: float,
          value_eur: float, unrealized, unrealized_pct, local, fx_effect) -> dict:
    return {
        "ticker": ticker,
        "asset_name": (meta.asset_name if meta else None) or pos.asset_name or ticker,
        "quantity": round(pos.quantity, 6),
        "currency": pos.currency,
        "avg_cost": round(pru, 4) if pru else None,
        "cost_eur": cost_eur,
        "price": round(price, 4) if priced else None,
        "price_currency": quote.get("currency") if priced else None,
        "price_date": quote.get("price_date") if priced else None,
        "price_stale": bool(quote.get("stale", True)) if priced else True,
        "priced": priced,
        "value_eur": round(value_eur, 2),
        "unrealized_eur": round(unrealized, 2) if unrealized is not None else None,
        "unrealized_pct": round(unrealized_pct, 2) if unrealized_pct is not None else None,
        "unrealized_local": round(local, 2) if local is not None else None,
        "fx_effect_eur": round(fx_effect, 2) if fx_effect is not None else None,
    }


async def value_positions(replay: Replay, tickers: list[str], quotes: dict, fx: FxBook,
                          holdings_meta: dict[str, PortfolioHolding]) -> PositionsValuation:
    """Valorise chaque position détenue ; les totaux se cumulent ligne à ligne, dans l'ordre des tickers."""
    out = PositionsValuation()
    for ticker in tickers:
        pos = replay.positions[ticker]
        quote = quotes.get(ticker, {})
        price = quote.get("price") or 0.0
        price_eur = quote.get("price_eur") or 0.0
        priced = price > 0 and price_eur > 0
        cost_eur = round(pos.cost_eur, 2) if pos.cost_eur else None
        pru = pos.cost / pos.quantity if pos.cost else None
        if priced:
            value_eur = pos.quantity * price_eur
            if quote.get("stale"):
                out.stale.append(ticker)
        elif cost_eur is not None:
            value_eur = cost_eur
            out.unpriced.append(ticker)
        else:
            value_eur = 0.0
            out.unpriced.append(ticker)

        line_unrealized = line_unrealized_pct = line_fx = line_local = None
        if priced and cost_eur:
            line_unrealized = value_eur - cost_eur
            line_unrealized_pct = line_unrealized / cost_eur * 100.0
            out.unrealized_eur += line_unrealized
            out.unrealized_cost_eur += cost_eur
            if pru:
                price_in_position = await fx.convert(price, quote.get("currency") or pos.currency, pos.currency)
                local_eur = None
                if price_in_position is not None:
                    line_local = (price_in_position - pru) * pos.quantity
                    local_eur = await fx.convert(line_local, pos.currency, "EUR")
                if local_eur is not None:
                    line_fx = line_unrealized - local_eur
                    out.fx_effect_eur += line_fx
        out.value_eur += value_eur
        out.lines.append(_line(ticker, pos, holdings_meta.get(ticker), quote, pru, cost_eur, priced, price, value_eur,
                               line_unrealized, line_unrealized_pct, line_local, line_fx))
    return out
