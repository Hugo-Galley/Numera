"""Courbe reconstituée d'un compte titres (valeur et capital investi), TWR et rapprochement avec le courtier."""
from datetime import date as date_type

from sqlalchemy.orm import Session

from app.domain.holdings import EPSILON, Replay
from app.domain.performance import twr
from app.domain.portfolio import history_point, reconciliation_line, sample_days
from app.repositories import portfolio as repo
from app.services.portfolio.books import FxBook, PriceBook, unit_price
from app.services.portfolio.cash import Capital


async def history_series(db: Session, account_id: int, replay: Replay, book: PriceBook, fx: FxBook, cap: Capital,
                         opening_cash: float, value: float, today_day: date_type,
                         currency: str) -> tuple[list[dict], float | None, list[dict]]:
    """(points de la courbe, TWR, lignes de rapprochement) depuis le Point Zéro des positions."""
    baseline_date = replay.baseline_date
    snapshots = repo.snapshots_since(db, account_id, baseline_date)
    # Avant le Point Zéro des positions : valeurs des relevés
    points: list[dict] = [
        history_point(snap.date.date().isoformat(), snap.current_value, cap.invested_at(snap.date.date()))
        for snap in repo.snapshots_before(db, account_id, baseline_date)
    ]
    flow_days = {e.date.date() for e in cap.events if e.external}
    snapshot_days = {s.date.date() for s in snapshots}
    days = sample_days(baseline_date.date(), today_day, flow_days | snapshot_days)

    quantities = {t: p.quantity for t, p in replay.baseline.items()}
    qty_events = sorted(replay.quantity_events, key=lambda e: e[0])
    cash_sorted = sorted(cap.events, key=lambda e: e.date)
    qi = ci = 0
    running_cash = opening_cash
    twr_points: list[tuple[date_type, float, float]] = []
    for day in days:
        while qi < len(qty_events) and qty_events[qi][0].date() <= day:
            _, ticker, delta = qty_events[qi]
            quantities[ticker] = quantities.get(ticker, 0.0) + delta
            qi += 1
        day_flow = 0.0
        while ci < len(cash_sorted) and cash_sorted[ci].date.date() <= day:
            running_cash += cash_sorted[ci].cash
            day_flow += cash_sorted[ci].external
            ci += 1
        total = running_cash
        for ticker, qty in quantities.items():
            if qty > EPSILON:
                unit = await unit_price(book, fx, ticker, day, currency)
                total += qty * (unit or 0.0)
        if day == today_day:
            total = value  # le dernier point reprend la valeur actuelle (dernier cours)
        points.append(history_point(day.isoformat(), total, cap.invested_at(day)))
        twr_points.append((day, total, day_flow))

    by_day = {p["date"]: p["value"] for p in points}
    reconciliation = [
        reconciliation_line(snap.date, snap.current_value, by_day[snap.date.date().isoformat()])
        for snap in snapshots
        if by_day.get(snap.date.date().isoformat()) is not None
    ]
    return points, twr(twr_points), reconciliation
