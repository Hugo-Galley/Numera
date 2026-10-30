"""Coût mensuel et annuel d'une récurrence en EUR."""
import pytest

from app.domain.subscriptions import recurring_costs


def test_recurring_costs_by_frequency_in_eur():
    assert recurring_costs(10.0, "monthly", 1.0) == (10.0, 120.0)
    assert recurring_costs(120.0, "yearly", 1.0) == pytest.approx((10.0, 120.0))
    assert recurring_costs(21.6, "monthly", 1.08) == pytest.approx((20.0, 240.0))


def test_unknown_frequency_costs_nothing():
    assert recurring_costs(10.0, "fortnightly", 1.0) == (0.0, 0.0)
