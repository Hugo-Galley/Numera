"""Calculs purs du bilan annuel."""
from datetime import datetime

from app.domain.wrapped import hours, pct_change, period


def test_pct_change():
    assert pct_change(150.0, 100.0) == 50.0
    assert pct_change(50.0, -100.0) == 150.0
    assert pct_change(10.0, 0.0) is None
    assert pct_change(10.0, 0.004) is None


def test_period_stops_after_last_month():
    assert period(2026, 5) == (datetime(2026, 1, 1), datetime(2026, 6, 1))
    assert period(2025, 12) == (datetime(2025, 1, 1), datetime(2026, 1, 1))


def test_hours_needs_an_hourly_rate():
    assert hours(250.0, 20.0) == 12.5
    assert hours(250.0, None) is None
