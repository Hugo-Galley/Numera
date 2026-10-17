"""Alignement de la première échéance d'une récurrence sur son jour du mois."""
from datetime import datetime
from unittest.mock import MagicMock

from app.core.finance import get_recurring_occurrences


def _rule(**kwargs):
    defaults = {"end_date": None, "excluded_months": None, "frequency": "monthly"}
    defaults.update(kwargs)
    return MagicMock(**defaults)


def test_monthly_start_before_day_of_month_first_occurrence_same_month():
    # Règle créée le 8 pour le 16 : la première échéance est le 16 du même mois, pas le 8.
    rt = _rule(start_date=datetime(2026, 10, 8), day_of_month=16)
    occs = get_recurring_occurrences(rt, datetime(2026, 10, 1), datetime(2026, 12, 31))
    assert occs == [datetime(2026, 10, 16), datetime(2026, 11, 16), datetime(2026, 12, 16)]


def test_monthly_start_after_day_of_month_first_occurrence_next_month():
    rt = _rule(start_date=datetime(2026, 10, 20), day_of_month=16)
    occs = get_recurring_occurrences(rt, datetime(2026, 10, 1), datetime(2026, 12, 31))
    assert occs == [datetime(2026, 11, 16), datetime(2026, 12, 16)]


def test_monthly_day_31_clamped_in_short_month():
    rt = _rule(start_date=datetime(2026, 2, 3), day_of_month=31)
    occs = get_recurring_occurrences(rt, datetime(2026, 1, 1), datetime(2026, 4, 1))
    assert occs == [datetime(2026, 2, 28), datetime(2026, 3, 31)]


def test_generation_after_aligned_start_resumes_on_day_of_month():
    # Cas réel : une ancienne échéance fantôme au 8 (= start_date) ne doit pas faire sauter le 16.
    rt = _rule(start_date=datetime(2026, 10, 8), day_of_month=16)
    occs = get_recurring_occurrences(rt, datetime(2026, 10, 8, 0, 0, 1), datetime(2026, 10, 17, 9, 0))
    assert occs == [datetime(2026, 10, 16)]


def test_quarterly_aligned_on_day_of_month():
    rt = _rule(start_date=datetime(2026, 1, 5), day_of_month=10, frequency="quarterly")
    occs = get_recurring_occurrences(rt, datetime(2026, 1, 1), datetime(2026, 12, 31))
    assert occs == [datetime(2026, 1, 10), datetime(2026, 4, 10), datetime(2026, 7, 10), datetime(2026, 10, 10)]
