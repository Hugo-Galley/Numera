"""Valeur d'ouverture d'un compte titres au Point Zéro : inventaire valorisé, espèces d'après le relevé."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.domain.holdings import Replay
from app.domain.portfolio import SNAPSHOT_MATCH_DAYS
from app.repositories import portfolio as repo
from app.services.portfolio.books import FxBook, PriceBook, unit_price


async def opening_value(db: Session, account_id: int, replay: Replay, book: PriceBook, fx: FxBook,
                        currency: str) -> tuple[float, float, bool]:
    """(valeur d'ouverture, espèces d'ouverture, valeur approchée au coût faute de cours)."""
    baseline_date = replay.baseline_date
    if baseline_date is None:
        return 0.0, 0.0, False
    opening_approx = False
    inventory_value = 0.0
    for ticker, pos in replay.baseline.items():
        unit = await unit_price(book, fx, ticker, baseline_date.date(), currency)
        if unit is not None:
            inventory_value += pos.quantity * unit
        elif pos.cost:
            converted = await fx.convert(pos.cost, pos.currency, currency, baseline_date.date())
            inventory_value += converted or 0.0
            opening_approx = True
        else:
            opening_approx = True
    snapshot = repo.latest_zero_point(db, account_id)
    if snapshot is None or abs((snapshot.date - baseline_date).days) > SNAPSHOT_MATCH_DAYS:
        snapshot = repo.latest_snapshot_until(db, account_id, baseline_date + timedelta(days=SNAPSHOT_MATCH_DAYS))
        if snapshot is not None and (baseline_date - snapshot.date).days > SNAPSHOT_MATCH_DAYS:
            snapshot = None
    if snapshot is not None:
        return max(snapshot.current_value, inventory_value), max(0.0, snapshot.current_value - inventory_value), opening_approx
    return inventory_value, 0.0, opening_approx
