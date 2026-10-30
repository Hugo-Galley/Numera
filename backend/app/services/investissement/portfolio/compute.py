"""Valeur, plus-values et performance d'un compte titres, calculées depuis les positions et les opérations.

Règles et constantes : `domain/portfolio.py` ; XIRR / TWR : `domain/performance.py`. Le calcul lit la base
et les cours stockés (`security_prices`), étape par étape : positions, flux, ouverture, revenus, courbe.
"""
from datetime import date as date_type
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.holdings import EPSILON
from app.domain.performance import xirr
from app.domain.portfolio import MIN_XIRR_DAYS, PRE_INVENTORY_RATIO, uses_positions
from app.integrations.currency import CurrencyConversionError, get_exchange_rates
from app.models.account import Account
from app.repositories.investissement import portfolio as repo
from app.services.investissement.holdings.replay import replay_account
from app.services.investissement.market.quotes import get_market_quotes
from app.services.investissement.portfolio.books import FxBook, PriceBook, ensure_history
from app.services.investissement.portfolio.cash import Capital, anchor_on_inventory, capital
from app.services.investissement.portfolio.history import history_series
from app.services.investissement.portfolio.income import dividend_totals, fees_eur, realized_summary
from app.services.investissement.portfolio.opening import opening_value
from app.services.investissement.portfolio.positions import PositionsValuation, value_positions


def _account_rate(rates: dict[str, float], currency: str) -> float:
    if currency == "EUR":
        return 1.0
    rate = rates.get(currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {currency}")
    return rate


def _performance(cap: Capital, baseline_date: datetime | None, opening: float, value: float, cash: float,
                 currency: str, warnings: list[str]) -> tuple[float | None, bool]:
    """Performance simple et fiabilité : des versements antérieurs à l'inventaire sans Point Zéro valorisé sont
    comptés dans le capital investi alors que la valeur ne contient que l'inventaire et ce qui suit → gain et
    XIRR aberrants."""
    net_invested = cap.reference_value + cap.external_total
    gain = value - net_invested
    performance_pct = gain / net_invested * 100.0 if net_invested > 0 else None
    unreliable = False
    if cap.reference is None and baseline_date is not None:
        before_inventory = sum(e.external for e in cap.flow_events if e.date <= baseline_date)
        if before_inventory > PRE_INVENTORY_RATIO * max(opening, 1.0):
            unreliable = True
            performance_pct = None
            warnings.append(
                f"Versements antérieurs à l'inventaire ({before_inventory:,.0f} {currency}) très supérieurs à sa "
                f"valeur d'ouverture ({opening:,.0f} {currency}) : performance non calculée. "
                "Définissez un Point Zéro valorisé pour la fiabiliser."
            )
    if cash < -0.01 * max(value, 1.0):
        warnings.append("Espèces négatives : il manque probablement un versement ou une vente dans l'historique.")
    return performance_pct, unreliable


def _xirr(cap: Capital, value: float, today_day: date_type, enabled: bool) -> tuple[list[tuple[date_type, float]], float | None, int]:
    """XIRR : valeur d'ouverture, flux externes, puis valeur actuelle. Renvoie (flux, XIRR, durée en jours)."""
    xirr_flows: list[tuple[date_type, float]] = []
    if cap.reference_date is not None and cap.reference_value > 0:
        xirr_flows.append((cap.reference_date.date(), -cap.reference_value))
    xirr_flows += [(e.date.date(), -e.external) for e in cap.flow_events]
    xirr_flows.append((today_day, value))
    first_flow_day = min((d for d, _ in xirr_flows), default=today_day)
    period_days = (today_day - first_flow_day).days
    # Annualiser une période de quelques jours produit des valeurs absurdes (« 49950 % ») : pas de XIRR
    return xirr_flows, (xirr(xirr_flows) if enabled and period_days >= MIN_XIRR_DAYS else None), period_days


def _result(account: Account, rate: float, valued: bool, baseline_date: datetime | None, positions: PositionsValuation,
            figures: dict, realized: tuple[dict[int, dict], float, int], dividends: tuple[float, float, float],
            history: tuple[list[dict] | None, float | None, list[dict] | None], latest_snapshot,
            warnings: list[str], xirr_flows: list[tuple[date_type, float]]) -> dict:
    """Dictionnaire de sortie (voir `schemas/portfolio.py::PortfolioRead`) ; montants arrondis au centime."""
    value, cash, net_invested, gain = figures["value"], figures["cash"], figures["net_invested"], figures["gain"]
    realized_by_year, realized_total, realized_unknown = realized
    series, twr_value, reconciliation = history

    def eur(amount: float) -> float:
        return amount / rate

    return {
        "account_id": account.id,
        "account_name": account.name,
        "currency": account.currency,
        "valued_by_positions": valued,
        "value_source": "positions" if valued else "snapshot",
        "baseline_date": baseline_date.isoformat() if baseline_date else None,
        "value": round(value, 2),
        "value_eur": round(eur(value), 2),
        "positions_value_eur": round(positions.value_eur, 2),
        "cash": round(cash, 2),
        "net_invested": round(net_invested, 2),
        "net_invested_eur": round(eur(net_invested), 2),
        "gain": round(gain, 2),
        "gain_eur": round(eur(gain), 2),
        "performance_pct": round(figures["performance_pct"], 2) if figures["performance_pct"] is not None else None,
        "xirr_pct": round(figures["xirr"] * 100.0, 2) if figures["xirr"] is not None else None,
        "performance_unreliable": figures["unreliable"],
        "twr_pct": round(twr_value * 100.0, 2) if twr_value is not None else None,
        "period_days": figures["period_days"],
        "unrealized_eur": round(positions.unrealized_eur, 2) if positions.unrealized_cost_eur else None,
        "unrealized_pct": round(positions.unrealized_eur / positions.unrealized_cost_eur * 100.0, 2) if positions.unrealized_cost_eur else None,
        "fx_effect_eur": round(positions.fx_effect_eur, 2) if positions.unrealized_cost_eur else None,
        "lines_without_cost": [ln["ticker"] for ln in positions.lines if ln["cost_eur"] is None],
        "realized_eur": round(realized_total, 2),
        "realized_unknown_sales": realized_unknown,
        "realized_by_year": [
            {**entry, "realized_eur": round(entry["realized_eur"], 2), "proceeds_eur": round(entry["proceeds_eur"], 2)}
            for entry in sorted(realized_by_year.values(), key=lambda e: e["year"], reverse=True)
        ],
        "dividends_eur": round(dividends[0], 2),
        "dividends_12m_eur": round(dividends[1], 2),
        "withholding_eur": round(dividends[2], 2),
        "fees_eur": round(figures["fees"], 2),
        "lines": positions.lines,
        "stale_tickers": positions.stale,
        "snapshot": (
            {"date": latest_snapshot.date.isoformat(), "value": round(latest_snapshot.current_value, 2)}
            if latest_snapshot
            else None
        ),
        "reconciliation": reconciliation,
        "history": series,
        "warnings": warnings,
        "_xirr_flows_eur": [(d, eur(a)) for d, a in xirr_flows],
    }


async def compute_portfolio(db: Session, account: Account, *, fetch: bool = True, history: bool = True) -> dict:
    """Indicateurs complets d'un compte (voir `schemas/portfolio.py::PortfolioRead`)."""
    today = datetime.now()
    today_day = today.date()
    currency = account.currency
    rate = _account_rate(await get_exchange_rates("EUR"), currency)  # unités de la devise du compte pour 1 EUR
    fx = FxBook(db)
    replay = await replay_account(db, account.id)
    baseline_date = replay.baseline_date
    valued = uses_positions(account, replay)
    warnings: list[str] = []

    holdings_meta = repo.holdings_meta(db, account.id)
    tickers = sorted(t for t, p in replay.positions.items() if p.quantity > EPSILON)
    quotes = await get_market_quotes(tickers, db=db) if tickers else {}
    positions = await value_positions(replay, tickers, quotes, fx, holdings_meta)
    if positions.unpriced:
        warnings.append(f"Aucun cours disponible pour {', '.join(positions.unpriced)} : valorisé au coût de revient.")

    cap = capital(db, account.id, baseline_date)
    book = PriceBook()
    history_start = baseline_date.date() if baseline_date else (cap.events[0].date.date() if cap.events else today_day)
    all_tickers = sorted(set(replay.positions) | set(replay.baseline) | {t for _, t, _ in replay.quantity_events})
    await ensure_history(db, book, all_tickers, history_start, fetch)
    opening, opening_cash, opening_approx = await opening_value(db, account.id, replay, book, fx, currency)
    if opening_approx:
        warnings.append("Cours du Point Zéro indisponibles : valeur d'ouverture estimée au coût de revient.")
    anchor_on_inventory(cap, baseline_date, opening)

    cash = opening_cash + sum(e.cash for e in cap.events)
    value = positions.value_eur * rate + cash
    net_invested = cap.reference_value + cap.external_total
    performance_pct, unreliable = _performance(cap, baseline_date, opening, value, cash, currency, warnings)

    realized = realized_summary(replay)
    dividends = await dividend_totals(db, account.id, today)
    fees = await fees_eur(db, account.id, baseline_date, currency, fx)

    series = twr_value = reconciliation = None
    history_missing = [t for t in all_tickers if not book.has(t)]
    if history and baseline_date is not None and valued and not history_missing:
        series, twr_value, reconciliation = await history_series(
            db, account.id, replay, book, fx, cap, opening_cash, value, today_day, currency
        )
    elif history and valued and history_missing:
        warnings.append(f"Historique de cours indisponible pour {', '.join(history_missing)} : courbe et rapprochement non calculés.")

    xirr_flows, xirr_value, period_days = _xirr(cap, value, today_day, valued and not unreliable)
    figures = {
        "value": value, "cash": cash, "net_invested": net_invested, "gain": value - net_invested,
        "performance_pct": performance_pct, "xirr": xirr_value, "unreliable": unreliable,
        "period_days": period_days, "fees": fees,
    }
    return _result(account, rate, valued, baseline_date, positions, figures, realized, dividends,
                   (series, twr_value, reconciliation), repo.latest_snapshot(db, account.id), warnings, xirr_flows)


async def positions_values_eur(db: Session, accounts: list[Account]) -> dict[int, float]:
    """Valeur actuelle en EUR (positions × cours + espèces) des comptes valorisés par leurs positions.

    Source unique pour toute vue qui affiche la valeur courante d'un compte titres (patrimoine,
    budget, investissements) : les autres comptes restent valorisés par relevé ou solde.
    """
    values: dict[int, float] = {}
    for account in accounts:
        if uses_positions(account, await replay_account(db, account.id)):
            values[account.id] = (await compute_portfolio(db, account, history=False))["value_eur"]
    return values
