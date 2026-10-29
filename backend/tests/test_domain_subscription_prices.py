"""Détection pure d'une hausse de prix sur une série de prélèvements."""
from datetime import datetime
from types import SimpleNamespace

from app.domain.subscription_prices import series_change


def _rows(amounts: list[float]) -> list[SimpleNamespace]:
    return [SimpleNamespace(date=datetime(2026, month, 10), amount=amount) for month, amount in enumerate(amounts, start=1)]


def test_series_change_detects_increase():
    change = series_change(_rows([13.49, 13.49, 13.49, 15.99]), now=datetime(2026, 4, 20))

    assert change is not None
    assert (change.old_amount, change.new_amount) == (13.49, 15.99)
    assert round(change.new_amount - change.old_amount, 2) == 2.5
    assert change.frequency == "monthly" and change.per_year == 12
    assert change.changed_on == datetime(2026, 4, 10).date()


def test_series_change_ignores_stable_price():
    assert series_change(_rows([13.49, 13.49, 13.49]), now=datetime(2026, 3, 20)) is None
