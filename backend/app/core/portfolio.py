"""Valeur, plus-values et performance d'un compte titres, calculées depuis les positions et les opérations.

Source de vérité d'un compte titres (PEA, CTO, crypto) : valeur = Σ quantité × cours + espèces, où
les espèces cumulent les flux d'opérations (`versement` +, `retrait` −, `achat` −, `vente` +, `frais` −,
`dividende` +) à partir de l'inventaire Point Zéro. Un versement/retrait portant un titre et une quantité
(ancien format « un seul mouvement ») est à la fois un flux externe et une opération : l'effet sur les
espèces s'annule. Les snapshots (`balance_snapshots`) ne servent plus qu'au rapprochement avec le relevé
du courtier.

Fonctions pures (`xirr`, `twr`) ; le reste lit la base et les cours stockés (`security_prices`).
"""
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date as date_type, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.currency import CurrencyConversionError, convert_amount, get_exchange_rates
from app.core.dividends import load_dividends_eur
from app.core.holdings import EPSILON, Replay, is_trade, replay_account
from app.core.logging import get_logger
from app.core.market_data import fetch_price_history, get_market_quotes
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.security_price import SecurityPrice
from app.models.transaction import Transaction

logger = get_logger(__name__)

RECONCILIATION_THRESHOLD_PCT = 2.0
SNAPSHOT_MATCH_DAYS = 7
HISTORY_RETRY = timedelta(hours=6)
_HISTORY_ATTEMPTS: dict[str, datetime] = {}

INTEREST_CATEGORIES = {"Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"}
FEE_KEYWORDS = ("achat", "frais", "commission", "tax")


# ── Fonctions pures ────────────────────────────────────────────────────────────

def xirr(flows: list[tuple[date_type, float]]) -> float | None:
    """Taux de rendement annualisé pondéré par les montants (flux < 0 : argent investi, > 0 : récupéré).

    Renvoie None s'il n'y a pas à la fois un flux positif et un flux négatif, ou pas de solution.
    """
    flows = [(d, a) for d, a in flows if a]
    if len(flows) < 2 or not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        return None
    origin = min(d for d, _ in flows)
    spans = [((d - origin).days / 365.0, a) for d, a in flows]

    def npv(rate: float) -> float:
        return sum(a / (1.0 + rate) ** t for t, a in spans)

    low, high = -0.9999, 1000.0
    f_low, f_high = npv(low), npv(high)
    if f_low * f_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid
    return (low + high) / 2.0


def twr(points: list[tuple[date_type, float, float]]) -> float | None:
    """Performance pondérée par le temps, indépendante du moment des versements.

    `points` : (jour, valeur en fin de journée, flux externe net du jour : versement − retrait), triés.
    Entre deux points, rendement = (valeur avant le flux du jour) / (valeur du point précédent).
    """
    if len(points) < 2:
        return None
    factor = 1.0
    previous = points[0][1]
    for _, value, flow in points[1:]:
        if previous > EPSILON:
            factor *= (value - flow) / previous
        previous = value
    return factor - 1.0


# ── Cours et taux historiques ──────────────────────────────────────────────────

class PriceBook:
    """Cours de clôture stockés, chargés en mémoire ; report du dernier cours connu les jours sans cotation."""

    def __init__(self) -> None:
        self._series: dict[str, tuple[list[date_type], list[float], list[str]]] = {}

    def load(self, db: Session, tickers: list[str]) -> None:
        for ticker in tickers:
            rows = (
                db.query(SecurityPrice.date, SecurityPrice.close, SecurityPrice.currency)
                .filter(SecurityPrice.ticker == ticker)
                .order_by(SecurityPrice.date.asc())
                .all()
            )
            self._series[ticker] = ([r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows])

    def has(self, ticker: str) -> bool:
        return bool(self._series.get(ticker, ([], [], []))[0])

    def covers(self, ticker: str, day: date_type, gap_days: int = SNAPSHOT_MATCH_DAYS) -> bool:
        dates = self._series.get(ticker, ([], [], []))[0]
        return bool(dates) and dates[0] <= day + timedelta(days=gap_days)

    def price_on(self, ticker: str, day: date_type) -> tuple[float, str] | None:
        """(cours, devise) à `day` ; avant le premier cours connu, on prend le premier (approximation)."""
        dates, closes, currencies = self._series.get(ticker, ([], [], []))
        if not dates:
            return None
        index = max(bisect_right(dates, day) - 1, 0)
        return closes[index], currencies[index]


async def ensure_history(db: Session, book: PriceBook, tickers: list[str], start: date_type, fetch: bool) -> None:
    """Charge les cours stockés ; télécharge l'historique manquant (au plus une tentative / 6 h par titre)."""
    book.load(db, tickers)
    if not fetch:
        return
    now = datetime.now()
    for ticker in tickers:
        if book.covers(ticker, start):
            continue
        last_try = _HISTORY_ATTEMPTS.get(ticker)
        if last_try and now - last_try < HISTORY_RETRY:
            continue
        _HISTORY_ATTEMPTS[ticker] = now
        try:
            await fetch_price_history(db, ticker, start - timedelta(days=SNAPSHOT_MATCH_DAYS))
        except Exception as exc:  # réseau, format inattendu : on continue avec ce qu'on a
            logger.warning(f"Price history unavailable for {ticker}: {exc}")
    book.load(db, tickers)


class FxBook:
    """Conversions datées mémorisées (une seule requête de taux par couple devise/jour)."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._memo: dict[tuple[str, str, date_type | None], float | None] = {}

    async def convert(self, amount: float, source: str, target: str, day: date_type | None = None) -> float | None:
        if source == target:
            return amount
        key = (source, target, day)
        if key not in self._memo:
            try:
                self._memo[key] = await convert_amount(1.0, source, target, date=day, db=self._db if day else None)
            except CurrencyConversionError as exc:
                logger.warning(f"Portfolio FX: {exc}")
                self._memo[key] = None
        unit = self._memo[key]
        return None if unit is None else amount * unit


# ── Flux ───────────────────────────────────────────────────────────────────────

@dataclass
class CashEvent:
    date: datetime
    cash: float  # variation des espèces (devise du compte)
    external: float = 0.0  # flux externe (versement + / retrait −), devise du compte


def classify_regular_flow(tx: Transaction) -> float:
    """Flux externe (signe) d'une transaction bancaire classique sur un compte titres, par mots-clés."""
    merchant = (tx.merchant or "").lower()
    if tx.type in ("Solde Initial", "Entree"):
        if tx.category and tx.category.name in INTEREST_CATEGORIES:
            return 0.0
        if "dividende" in merchant:
            return 0.0
        return -tx.amount if "vente" in merchant else tx.amount
    if tx.type == "Sortie":
        return 0.0 if any(k in merchant for k in FEE_KEYWORDS) else -tx.amount
    return 0.0


def cash_events(db: Session, account_id: int, after: datetime | None) -> tuple[list[CashEvent], bool]:
    """Variations d'espèces datées après `after`. Renvoie aussi si le compte a des opérations d'investissement."""
    query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    all_txs = query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()
    events: list[CashEvent] = []
    for tx in all_txs:
        if after is not None and tx.date <= after:
            continue
        trade = is_trade(tx.type, tx.ticker, tx.quantity)
        if tx.type == "versement":
            events.append(CashEvent(tx.date, 0.0 if trade else tx.amount, tx.amount))
        elif tx.type == "retrait":
            events.append(CashEvent(tx.date, 0.0 if trade else -tx.amount, -tx.amount))
        elif tx.type in ("vente", "dividende"):
            events.append(CashEvent(tx.date, tx.amount))
        elif tx.type in ("achat", "frais"):
            events.append(CashEvent(tx.date, -tx.amount))
    if all_txs:
        return events, True

    regular = (
        db.query(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    for tx in regular:
        if after is not None and tx.date <= after:
            continue
        flow = classify_regular_flow(tx)
        if flow:
            events.append(CashEvent(tx.date, flow, flow))
    return events, False


# ── Calcul principal ───────────────────────────────────────────────────────────

def _account_rate(rates: dict[str, float], currency: str) -> float:
    if currency == "EUR":
        return 1.0
    rate = rates.get(currency)
    if not rate:
        raise CurrencyConversionError(f"No exchange rate available for {currency}")
    return rate


def _sample_days(start: date_type, end: date_type, extra: set[date_type]) -> list[date_type]:
    span = max((end - start).days, 1)
    step = max(7, -(-span // 300))
    days = {start, end} | {d for d in extra if start <= d <= end}
    day = start
    while day < end:
        days.add(day)
        day += timedelta(days=step)
    return sorted(days)


def uses_positions(account: Account, replay: Replay) -> bool:
    """Un compte titres est valorisé par ses positions dès qu'il en a (ou a eu) ; l'assurance-vie reste au snapshot."""
    return account.type == "investissement" and bool(replay.positions or replay.baseline or replay.realized)


async def compute_portfolio(db: Session, account: Account, *, fetch: bool = True, history: bool = True) -> dict:
    """Indicateurs complets d'un compte (voir `schemas/portfolio.py::PortfolioRead`)."""
    today = datetime.now()
    today_day = today.date()
    currency = account.currency
    rates = await get_exchange_rates("EUR")
    rate = _account_rate(rates, currency)  # unités de la devise du compte pour 1 EUR
    fx = FxBook(db)

    replay = await replay_account(db, account.id)
    baseline_date = replay.baseline_date
    valued_by_positions = uses_positions(account, replay)
    warnings: list[str] = []

    # ── Positions actuelles valorisées au dernier cours ──
    holdings_meta = {h.ticker: h for h in db.query(PortfolioHolding).filter(PortfolioHolding.account_id == account.id).all()}
    tickers = sorted(t for t, p in replay.positions.items() if p.quantity > EPSILON)
    quotes = await get_market_quotes(tickers, db=db) if tickers else {}

    lines: list[dict] = []
    value_eur_positions = 0.0
    unrealized_eur = 0.0
    unrealized_cost_eur = 0.0
    fx_effect_eur = 0.0
    cost_known_eur = 0.0
    unpriced: list[str] = []
    stale: list[str] = []
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
                stale.append(ticker)
        elif cost_eur is not None:
            value_eur = cost_eur
            unpriced.append(ticker)
        else:
            value_eur = 0.0
            unpriced.append(ticker)

        line_unrealized = line_unrealized_pct = line_fx = line_local = None
        if priced and cost_eur:
            line_unrealized = value_eur - cost_eur
            line_unrealized_pct = line_unrealized / cost_eur * 100.0
            unrealized_eur += line_unrealized
            unrealized_cost_eur += cost_eur
            if pru:
                price_in_position = await fx.convert(price, quote.get("currency") or pos.currency, pos.currency)
                local_eur = None
                if price_in_position is not None:
                    line_local = (price_in_position - pru) * pos.quantity
                    local_eur = await fx.convert(line_local, pos.currency, "EUR")
                if local_eur is not None:
                    line_fx = line_unrealized - local_eur
                    fx_effect_eur += line_fx
        if cost_eur:
            cost_known_eur += cost_eur
        value_eur_positions += value_eur
        meta = holdings_meta.get(ticker)
        lines.append(
            {
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
                "unrealized_eur": round(line_unrealized, 2) if line_unrealized is not None else None,
                "unrealized_pct": round(line_unrealized_pct, 2) if line_unrealized_pct is not None else None,
                "unrealized_local": round(line_local, 2) if line_local is not None else None,
                "fx_effect_eur": round(line_fx, 2) if line_fx is not None else None,
            }
        )
    if unpriced:
        warnings.append(f"Aucun cours disponible pour {', '.join(unpriced)} : valorisé au coût de revient.")
    lines_without_cost = [ln["ticker"] for ln in lines if ln["cost_eur"] is None]

    # ── Flux et espèces ──
    events, _ = cash_events(db, account.id, baseline_date)
    cash_delta = sum(e.cash for e in events)
    external_total = sum(e.external for e in events)

    # ── Valeur d'ouverture (Point Zéro) ──
    book = PriceBook()
    history_start = baseline_date.date() if baseline_date else (events[0].date.date() if events else today_day)
    all_tickers = sorted(set(replay.positions) | set(replay.baseline) | {t for _, t, _ in replay.quantity_events})
    await ensure_history(db, book, all_tickers, history_start, fetch)

    async def unit_price_acct(ticker: str, day: date_type) -> float | None:
        found = book.price_on(ticker, day)
        if found is None:
            return None
        return await fx.convert(found[0], found[1], currency, day)

    opening_value = 0.0
    opening_cash = 0.0
    opening_approx = False
    if baseline_date is not None:
        inventory_value = 0.0
        for ticker, pos in replay.baseline.items():
            unit = await unit_price_acct(ticker, baseline_date.date())
            if unit is not None:
                inventory_value += pos.quantity * unit
            elif pos.cost:
                converted = await fx.convert(pos.cost, pos.currency, currency, baseline_date.date())
                inventory_value += converted or 0.0
                opening_approx = True
            else:
                opening_approx = True
        snapshot = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.is_zero_point.is_(True))
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if snapshot is None or abs((snapshot.date - baseline_date).days) > SNAPSHOT_MATCH_DAYS:
            snapshot = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date <= baseline_date + timedelta(days=SNAPSHOT_MATCH_DAYS))
                .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
                .first()
            )
            if snapshot is not None and (baseline_date - snapshot.date).days > SNAPSHOT_MATCH_DAYS:
                snapshot = None
        if snapshot is not None:
            opening_cash = max(0.0, snapshot.current_value - inventory_value)
            opening_value = max(snapshot.current_value, inventory_value)
        else:
            opening_value = inventory_value
        if opening_approx:
            warnings.append("Cours du Point Zéro indisponibles : valeur d'ouverture estimée au coût de revient.")

    cash = opening_cash + cash_delta
    value = value_eur_positions * rate + cash
    net_invested = opening_value + external_total
    gain = value - net_invested
    performance_pct = gain / net_invested * 100.0 if net_invested > 0 else None
    if cash < -0.01 * max(value, 1.0):
        warnings.append("Espèces négatives : il manque probablement un versement ou une vente dans l'historique.")

    # ── Plus-values réalisées ──
    realized_by_year: dict[int, dict] = {}
    realized_total = 0.0
    realized_unknown = 0
    for sale in replay.realized:
        entry = realized_by_year.setdefault(sale.date.year, {"year": sale.date.year, "realized_eur": 0.0, "proceeds_eur": 0.0, "sales": 0})
        entry["sales"] += 1
        if sale.realized_eur is None:
            realized_unknown += 1
            continue
        entry["realized_eur"] += sale.realized_eur
        entry["proceeds_eur"] += sale.proceeds_eur or 0.0
        realized_total += sale.realized_eur

    # ── Dividendes et frais (EUR) ──
    dividend_rows = await load_dividends_eur(db, account.id)
    since = today - timedelta(days=365)
    dividends_net = sum(r.net_eur for r in dividend_rows)
    dividends_12m = sum(r.net_eur for r in dividend_rows if r.tx.date >= since)
    dividends_tax = sum(r.tax_eur for r in dividend_rows)

    fees_eur = 0.0
    fee_txs = (
        db.query(InvestmentTransaction)
        .filter(InvestmentTransaction.account_id == account.id)
        .all()
    )
    for tx in fee_txs:
        if baseline_date is not None and tx.date <= baseline_date:
            continue
        if tx.type == "frais":
            converted = await fx.convert(tx.amount, currency, "EUR", tx.date.date())
        elif tx.fees and tx.type in ("achat", "vente", "versement", "retrait") and is_trade(tx.type, tx.ticker, tx.quantity):
            converted = await fx.convert(tx.fees, (tx.price_currency or tx.currency or "EUR").upper(), "EUR", tx.date.date())
        else:
            continue
        fees_eur += converted or 0.0

    # ── Historique reconstitué, XIRR, TWR, rapprochement ──
    series: list[dict] | None = None
    reconciliation: list[dict] | None = None
    twr_value = None
    history_missing = [t for t in all_tickers if not book.has(t)]
    snapshots = []
    if baseline_date is not None:
        snapshots = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date >= baseline_date)
            .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
            .all()
        )

    if history and baseline_date is not None and valued_by_positions and not history_missing:
        flow_days = {e.date.date() for e in events if e.external}
        snapshot_days = {s.date.date() for s in snapshots}
        days = _sample_days(baseline_date.date(), today_day, flow_days | snapshot_days)

        quantities = {t: p.quantity for t, p in replay.baseline.items()}
        qty_events = sorted(replay.quantity_events, key=lambda e: e[0])
        cash_sorted = sorted(events, key=lambda e: e.date)
        qi = ci = 0
        running_cash = opening_cash
        running_external = 0.0
        points: list[dict] = []
        twr_points: list[tuple[date_type, float, float]] = []
        for day in days:
            while qi < len(qty_events) and qty_events[qi][0].date() <= day:
                _, ticker, delta = qty_events[qi]
                quantities[ticker] = quantities.get(ticker, 0.0) + delta
                qi += 1
            day_flow = 0.0
            while ci < len(cash_sorted) and cash_sorted[ci].date.date() <= day:
                running_cash += cash_sorted[ci].cash
                running_external += cash_sorted[ci].external
                day_flow += cash_sorted[ci].external
                ci += 1
            total = running_cash
            for ticker, qty in quantities.items():
                if qty > EPSILON:
                    unit = await unit_price_acct(ticker, day)
                    total += qty * (unit or 0.0)
            if day == today_day:
                total = value  # le dernier point reprend la valeur actuelle (dernier cours)
            invested = opening_value + running_external
            points.append(
                {
                    "date": day.isoformat(),
                    "value": round(total, 2),
                    "net_invested": round(invested, 2),
                    "gain": round(total - invested, 2),
                    "performance_pct": round((total - invested) / invested * 100.0, 2) if invested > 0 else None,
                }
            )
            twr_points.append((day, total, day_flow))
        series = points
        twr_value = twr(twr_points)

        by_day = {p["date"]: p["value"] for p in points}
        reconciliation = []
        for snap in snapshots:
            computed = by_day.get(snap.date.date().isoformat())
            if computed is None:
                continue
            gap = computed - snap.current_value
            gap_pct = gap / snap.current_value * 100.0 if snap.current_value else None
            reconciliation.append(
                {
                    "date": snap.date.isoformat(),
                    "snapshot_value": round(snap.current_value, 2),
                    "computed_value": round(computed, 2),
                    "gap": round(gap, 2),
                    "gap_pct": round(gap_pct, 2) if gap_pct is not None else None,
                    "flagged": gap_pct is not None and abs(gap_pct) > RECONCILIATION_THRESHOLD_PCT,
                }
            )
    elif history and valued_by_positions and history_missing:
        warnings.append(f"Historique de cours indisponible pour {', '.join(history_missing)} : courbe et rapprochement non calculés.")

    # XIRR : valeur d'ouverture, flux externes, puis valeur actuelle
    xirr_flows: list[tuple[date_type, float]] = []
    if baseline_date is not None and opening_value > 0:
        xirr_flows.append((baseline_date.date(), -opening_value))
    xirr_flows += [(e.date.date(), -e.external) for e in events if e.external]
    xirr_flows.append((today_day, value))
    xirr_value = xirr(xirr_flows) if valued_by_positions else None
    first_flow_day = min((d for d, _ in xirr_flows), default=today_day)
    period_days = (today_day - first_flow_day).days

    latest_snapshot = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account.id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )

    def eur(amount: float) -> float:
        return amount / rate

    return {
        "account_id": account.id,
        "account_name": account.name,
        "currency": currency,
        "valued_by_positions": valued_by_positions,
        "value_source": "positions" if valued_by_positions else "snapshot",
        "baseline_date": baseline_date.isoformat() if baseline_date else None,
        "value": round(value, 2),
        "value_eur": round(eur(value), 2),
        "positions_value_eur": round(value_eur_positions, 2),
        "cash": round(cash, 2),
        "net_invested": round(net_invested, 2),
        "net_invested_eur": round(eur(net_invested), 2),
        "gain": round(gain, 2),
        "gain_eur": round(eur(gain), 2),
        "performance_pct": round(performance_pct, 2) if performance_pct is not None else None,
        "xirr_pct": round(xirr_value * 100.0, 2) if xirr_value is not None else None,
        "twr_pct": round(twr_value * 100.0, 2) if twr_value is not None else None,
        "period_days": period_days,
        "unrealized_eur": round(unrealized_eur, 2) if unrealized_cost_eur else None,
        "unrealized_pct": round(unrealized_eur / unrealized_cost_eur * 100.0, 2) if unrealized_cost_eur else None,
        "fx_effect_eur": round(fx_effect_eur, 2) if unrealized_cost_eur else None,
        "lines_without_cost": lines_without_cost,
        "realized_eur": round(realized_total, 2),
        "realized_unknown_sales": realized_unknown,
        "realized_by_year": [
            {**entry, "realized_eur": round(entry["realized_eur"], 2), "proceeds_eur": round(entry["proceeds_eur"], 2)}
            for entry in sorted(realized_by_year.values(), key=lambda e: e["year"], reverse=True)
        ],
        "dividends_eur": round(dividends_net, 2),
        "dividends_12m_eur": round(dividends_12m, 2),
        "withholding_eur": round(dividends_tax, 2),
        "fees_eur": round(fees_eur, 2),
        "lines": lines,
        "stale_tickers": stale,
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
