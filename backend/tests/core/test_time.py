"""Horloge unique (`app.core.time`) : figeable d'un seul point en test."""
from datetime import UTC, date, datetime

from freezegun import freeze_time

from app.core import time as clock


@freeze_time("2026-03-04 22:30:00")
def test_now_local_and_today_local_follow_frozen_clock():
    assert clock.now_local() == datetime(2026, 3, 4, 22, 30)
    assert clock.today_local() == date(2026, 3, 4)


@freeze_time("2026-03-04 22:30:00")
def test_utc_helpers_are_aware_or_naive_as_named():
    assert clock.utcnow_aware() == datetime(2026, 3, 4, 22, 30, tzinfo=UTC)
    assert clock.utcnow_naive() == datetime(2026, 3, 4, 22, 30)
    assert clock.now_local().tzinfo is None


@freeze_time("2026-03-04 22:30:00")
def test_end_of_today_is_tomorrow_midnight():
    assert clock.end_of_today() == datetime(2026, 3, 5)
