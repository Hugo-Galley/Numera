"""Stock picking face à un indice de référence : portefeuille fantôme rejoué ligne par ligne (sans base).

Chaque achat d'une action est rejoué le même jour, pour le même montant (frais compris), dans la référence ;
une vente d'une fraction f de la ligne vend la même fraction f du fantôme de cette ligne. Les dividendes nets
comptent côté actions seulement (référence supposée capitalisante). Un cours manquant marque la ligne
(`missing_price`, aussi pour un montant inconnu) : jamais de zéro silencieux, et la ligne sort des totaux.
"""
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.domain.holdings import EPSILON, Replay
from app.domain.performance import xirr
from app.domain.portfolio import MIN_XIRR_DAYS


@dataclass
class LineEvent:
    """Opération d'une ligne d'actions, en EUR."""

    day: date
    kind: str  # "buy" | "sell" | "dividend"
    amount_eur: float | None  # achat : montant frais compris ; vente : produit net ; dividende : net (None = inconnu)
    fraction: float = 0.0  # vente : part de la ligne cédée (0..1)
    benchmark_price_eur: float | None = None  # cours de la référence ce jour (achat, vente)


def _rate_pct(flows: list[tuple[date, float]], start: date | None, today: date) -> float | None:
    """XIRR en %, sauf sur une période trop courte pour être annualisée (cf. `MIN_XIRR_DAYS`)."""
    if start is None or (today - start).days < MIN_XIRR_DAYS:
        return None
    rate = xirr(flows)
    return round(rate * 100.0, 2) if rate is not None else None


def _round(amount: float | None) -> float | None:
    return round(amount, 2) if amount is not None else None


def compare_line(ticker: str, events: list[LineEvent], value_eur: float | None, benchmark_price_eur: float | None,
                 today: date) -> dict[str, Any]:
    """Une ligne face à son fantôme : totaux (valeur + produits [+ dividendes]), écart et XIRR des deux côtés.

    `value_eur` : valeur actuelle de la ligne (None = sans cours) ; `benchmark_price_eur` : cours actuel de la référence.
    """
    ordered = sorted(events, key=lambda e: (e.day, e.kind != "buy"))
    missing = value_eur is None or not benchmark_price_eur
    units = invested = proceeds = dividends = ghost_proceeds = 0.0
    stock_flows: list[tuple[date, float]] = []
    ghost_flows: list[tuple[date, float]] = []
    for event in ordered:
        amount = event.amount_eur
        if amount is None:  # montant sans taux de change, ou ligne du Point Zéro sans prix de revient
            missing, amount = True, 0.0
        if event.kind == "dividend":
            dividends += amount
            stock_flows.append((event.day, amount))
            continue
        price = event.benchmark_price_eur
        if not price or price <= EPSILON:
            missing = True
            price = None
        if event.kind == "buy":
            invested += amount
            stock_flows.append((event.day, -amount))
            ghost_flows.append((event.day, -amount))
            if price is not None:
                units += amount / price
        else:
            proceeds += amount
            stock_flows.append((event.day, amount))
            sold = units * min(max(event.fraction, 0.0), 1.0)
            units -= sold
            if price is not None:
                ghost_proceeds += sold * price
                ghost_flows.append((event.day, sold * price))

    start = ordered[0].day if ordered else None
    stock_total = (value_eur + proceeds + dividends) if value_eur is not None else None
    ghost_value = units * benchmark_price_eur if benchmark_price_eur and not missing else None
    ghost_total = ghost_value + ghost_proceeds if ghost_value is not None else None
    if value_eur is not None:
        stock_flows.append((today, value_eur))
    if ghost_value is not None:
        ghost_flows.append((today, ghost_value))
    return {
        "ticker": ticker,
        "start_date": start,
        "invested_eur": round(invested, 2),
        "stock_value_eur": _round(value_eur),
        "stock_proceeds_eur": round(proceeds, 2),
        "dividends_eur": round(dividends, 2),
        "stock_total_eur": _round(stock_total),
        "benchmark_value_eur": _round(ghost_value),
        "benchmark_proceeds_eur": round(ghost_proceeds, 2) if not missing else None,
        "benchmark_total_eur": _round(ghost_total),
        "gap_eur": _round(stock_total - ghost_total) if stock_total is not None and ghost_total is not None else None,
        "stock_xirr_pct": _rate_pct(stock_flows, start, today) if value_eur is not None else None,
        "benchmark_xirr_pct": _rate_pct(ghost_flows, start, today) if not missing else None,
        "missing_price": missing,
        "_stock_flows": stock_flows,
        "_benchmark_flows": ghost_flows,
    }


def compare_lines(lines: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """Totaux des lignes complètes (les lignes à cours manquant sont listées dans `incomplete_tickers`)."""
    complete = [line for line in lines if not line["missing_price"]]
    starts = [line["start_date"] for line in complete if line["start_date"] is not None]
    start = min(starts) if starts else None
    stock_total = sum(line["stock_total_eur"] for line in complete)
    ghost_total = sum(line["benchmark_total_eur"] for line in complete)

    def merged(key: str) -> list[tuple[date, float]]:
        by_day: dict[date, float] = {}
        for line in complete:
            for day, amount in line[key]:
                by_day[day] = by_day.get(day, 0.0) + amount
        return sorted(by_day.items())

    return {
        "start_date": start,
        "invested_eur": round(sum(line["invested_eur"] for line in complete), 2),
        "stock_value_eur": round(sum(line["stock_value_eur"] for line in complete), 2),
        "stock_proceeds_eur": round(sum(line["stock_proceeds_eur"] for line in complete), 2),
        "dividends_eur": round(sum(line["dividends_eur"] for line in complete), 2),
        "stock_total_eur": round(stock_total, 2),
        "benchmark_value_eur": round(sum(line["benchmark_value_eur"] for line in complete), 2),
        "benchmark_proceeds_eur": round(sum(line["benchmark_proceeds_eur"] for line in complete), 2),
        "benchmark_total_eur": round(ghost_total, 2),
        "gap_eur": round(stock_total - ghost_total, 2),
        "stock_xirr_pct": _rate_pct(merged("_stock_flows"), start, today) if complete else None,
        "benchmark_xirr_pct": _rate_pct(merged("_benchmark_flows"), start, today) if complete else None,
        "incomplete_tickers": [line["ticker"] for line in lines if line["missing_price"]],
    }


def stock_line_events(replay: Replay, dividends: list[tuple[date, str, float, bool]], excluded: set[str]) -> dict[str, list[LineEvent]]:
    """Opérations des lignes d'actions d'un compte (cours de la référence à remplir par l'appelant).

    - ligne du Point Zéro : départ à sa date pour son prix de revient (`cost_eur`, None s'il est inconnu) ;
    - achat (frais compris) et vente (fraction de la ligne cédée) rejoués ;
    - dividende net, compté à partir du début de la ligne. Un dividende réinvesti et l'achat qu'il génère
      s'annulent (l'argent ne sort pas du titre) : ni l'un ni l'autre n'est rejoué dans la référence.
    `dividends` : (jour, ticker, net EUR, réinvesti) ; `excluded` : tickers hors stock picking (ETF).
    """
    events: dict[str, list[LineEvent]] = {}
    for ticker, pos in replay.baseline.items():
        if ticker in excluded or pos.quantity <= EPSILON:
            continue
        start = (pos.cutoff or replay.baseline_date)
        if start is not None:
            events.setdefault(ticker, []).append(LineEvent(start.date(), "buy", pos.cost_eur or None))
    for trade in replay.trades:
        if trade.ticker in excluded or trade.reinvested:
            continue
        if trade.kind == "buy":
            events.setdefault(trade.ticker, []).append(LineEvent(trade.date.date(), "buy", trade.amount_eur))
        elif trade.held_before > EPSILON:
            fraction = trade.quantity / trade.held_before
            events.setdefault(trade.ticker, []).append(LineEvent(trade.date.date(), "sell", trade.amount_eur, fraction=fraction))
    for day, ticker, net_eur, reinvested in dividends:
        line = events.get(ticker)
        if line and not reinvested and day >= min(e.day for e in line):
            line.append(LineEvent(day, "dividend", net_eur))
    return events


def largest(values: dict[str, float]) -> str | None:
    """Ticker de plus forte valeur (référence par défaut : l'ETF le plus gros du portefeuille)."""
    return max(sorted(values), key=lambda t: values[t]) if values else None
