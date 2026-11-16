"""Stock picking face à un indice de référence (« portefeuille fantôme »).

Périmètre : titres non reliés à un profil ETF, sur les comptes `investissement` à soi valorisés par positions.
Référence : paramètre `benchmark`, sinon réglage `benchmark_ticker` (`system_settings`), sinon l'ETF de plus
forte valeur actuelle. Calculs purs : `domain/benchmark.py` ; cours : `security_prices` (`PriceBook`).
"""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.i18n import tr
from app.core.time import now_local
from app.db.system_settings import get_setting, set_setting
from app.domain.benchmark import LineEvent, compare_line, compare_lines, largest, stock_line_events
from app.domain.holdings import EPSILON, Replay, normalize_ticker
from app.domain.portfolio import uses_positions
from app.models.account import Account
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.analytics import investments as accounts_repo
from app.repositories.investissement import portfolio as repo
from app.services.investissement.dividends import load_dividends_eur
from app.services.investissement.holdings.replay import replay_account
from app.services.investissement.market.quotes import get_market_quotes, persist_fetched_prices
from app.services.investissement.portfolio import compute_portfolio
from app.services.investissement.portfolio.books import FxBook, PriceBook, ensure_history, unit_price

SETTING_KEY = "benchmark_ticker"


class _Account:
    """Compte titres rejoué : positions, métadonnées des lignes et valeur actuelle de chaque ligne."""

    def __init__(self, account: Account, replay: Replay, meta: dict[str, PortfolioHolding], lines: list[dict[str, Any]]) -> None:
        self.account = account
        self.replay = replay
        self.meta = meta
        self.values = {ln["ticker"]: (ln["value_eur"] if ln["priced"] else None) for ln in lines}
        self.names = {ln["ticker"]: ln["asset_name"] for ln in lines}

    def etf_tickers(self) -> set[str]:
        tickers = {t for t, p in self.replay.positions.items() if p.etf_profile_id is not None}
        tickers |= {t for t, p in self.replay.baseline.items() if p.etf_profile_id is not None}
        return tickers | {t for t, h in self.meta.items() if h.etf_profile_id is not None}


async def _accounts(db: Session) -> list[_Account]:
    out = []
    for account in accounts_repo.securities_accounts(db):
        replay = await replay_account(db, account.id)
        if not uses_positions(account, replay):
            continue
        portfolio = await compute_portfolio(db, account, history=False)
        out.append(_Account(account, replay, repo.holdings_meta(db, account.id), portfolio["lines"]))
    return out


def _choose(benchmark: str | None, setting: str | None, accounts: list[_Account]) -> tuple[str | None, str]:
    if benchmark:
        return normalize_ticker(benchmark), "query"
    if setting:
        return normalize_ticker(setting), "setting"
    etf_values: dict[str, float] = {}
    for acc in accounts:
        for ticker in acc.etf_tickers():
            etf_values[ticker] = etf_values.get(ticker, 0.0) + (acc.values.get(ticker) or 0.0)
    return largest(etf_values), "largest_etf"


def _candidates(accounts: list[_Account]) -> list[dict[str, str]]:
    """ETF détenus (sélecteur de référence)."""
    seen: dict[str, str] = {}
    for acc in accounts:
        for ticker in sorted(acc.etf_tickers()):
            seen.setdefault(ticker, acc.names.get(ticker) or (acc.meta[ticker].asset_name if ticker in acc.meta else ticker))
    return [{"ticker": t, "name": n} for t, n in sorted(seen.items())]


def _benchmark_meta(accounts: list[_Account], ticker: str) -> tuple[str | None, bool | None]:
    """(nom, verse des dividendes) de la référence d'après les lignes détenues ; None si elle n'est pas détenue."""
    holdings = [acc.meta[ticker] for acc in accounts if ticker in acc.meta]
    name = next((h.asset_name for h in holdings if h.asset_name), None)
    flags = [h.pays_dividends for h in holdings if h.pays_dividends is not None]
    return name, (any(flags) if flags else None)


async def _price_events(db: Session, ticker: str, lines: dict[tuple[int, str], list[LineEvent]]) -> float | None:
    """Remplit le cours (EUR) de la référence à chaque achat / vente ; renvoie son cours actuel en EUR."""
    days = sorted({e.day for events in lines.values() for e in events if e.kind != "dividend"})
    book, fx = PriceBook(), FxBook(db)
    if days:
        await ensure_history(db, book, [ticker], days[0], fetch=True)
    prices: dict[date, float | None] = {}
    for day in days:
        prices[day] = await unit_price(book, fx, ticker, day, "EUR") if book.covers(ticker, day) else None
    for events in lines.values():
        for event in events:
            if event.kind != "dividend":
                event.benchmark_price_eur = prices[event.day]
    quote = (await get_market_quotes([ticker], db=db)).get(ticker, {})
    persist_fetched_prices(db)  # valide les cours téléchargés (seul effet de bord, comme `compute_portfolio`)
    current = quote.get("price_eur") or 0.0
    return current if current > EPSILON else None


async def stock_picking_benchmark(db: Session, account_id: int | None = None, benchmark: str | None = None) -> dict[str, Any]:
    """Lignes d'actions face au même argent placé, aux mêmes dates, dans la référence (voir `domain/benchmark.py`)."""
    today = now_local().date()
    accounts = await _accounts(db)
    ticker, source = _choose(benchmark, get_setting(db, SETTING_KEY), accounts)
    scope = [acc for acc in accounts if account_id is None or acc.account.id == account_id]
    warnings: list[str] = []
    result: dict[str, Any] = {
        "account_id": account_id, "benchmark_ticker": ticker, "benchmark_source": source,
        "benchmark_name": None, "benchmark_distributes": None, "candidates": _candidates(accounts),
    }
    if ticker is None:
        warnings.append(tr("benchmark.warn_no_reference"))
        return {**result, **compare_lines([], today), "lines": [], "warnings": warnings}

    dividend_rows = await load_dividends_eur(db, account_id)
    events: dict[tuple[int, str], list[LineEvent]] = {}
    for acc in scope:
        dividends = [(r.tx.date.date(), normalize_ticker(r.tx.ticker), r.net_eur, r.tx.reinvested)
                     for r in dividend_rows if r.tx.account_id == acc.account.id and r.tx.ticker]
        for line_ticker, line_events in stock_line_events(acc.replay, dividends, acc.etf_tickers() | {ticker}).items():
            events[(acc.account.id, line_ticker)] = line_events
    current = await _price_events(db, ticker, events)

    by_id = {acc.account.id: acc for acc in scope}
    lines = []
    for (acc_id, line_ticker), line_events in sorted(events.items()):
        acc = by_id[acc_id]
        line = compare_line(line_ticker, line_events, acc.values.get(line_ticker, 0.0), current, today)
        line.update(account_id=acc_id, account_name=acc.account.name,
                    asset_name=acc.names.get(line_ticker) or acc.replay.positions[line_ticker].asset_name or line_ticker)
        lines.append(line)

    name, distributes = _benchmark_meta(accounts, ticker)
    if distributes:
        warnings.append(tr("benchmark.warn_distributes", ticker=ticker))
    if current is None:
        warnings.append(tr("benchmark.warn_no_quote", ticker=ticker))
    totals = compare_lines(lines, today)
    if totals["incomplete_tickers"]:
        warnings.append(tr("benchmark.warn_incomplete", tickers=", ".join(totals["incomplete_tickers"])))
    public_lines = [{k: v for k, v in line.items() if not k.startswith("_")} for line in lines]
    return {**result, **totals, "benchmark_name": name or ticker, "benchmark_distributes": distributes,
            "lines": public_lines, "warnings": warnings}


def set_benchmark(db: Session, ticker: str | None) -> dict[str, str | None]:
    """Enregistre la référence choisie (vide : retour à l'ETF de plus forte valeur)."""
    value = normalize_ticker(ticker) if ticker and ticker.strip() else ""
    set_setting(db, SETTING_KEY, value)
    db.commit()
    return {"ticker": value or None}
