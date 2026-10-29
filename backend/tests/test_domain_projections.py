"""Projections pures : objectif FIRE, prévision de patrimoine, simulation."""
import pytest

from app.domain.projections import (
    fire_target,
    months_to_target,
    parse_events,
    project_wealth,
    simulate_wealth,
)


def test_months_to_target():
    assert months_to_target(1000.0, 100.0, 0.0, 500.0) == 0
    assert months_to_target(0.0, 100.0, 0.0, 1000.0) == 10
    assert months_to_target(0.0, 0.0, 0.0, 1000.0) is None


def test_fire_target_is_expenses_over_withdrawal_rate():
    assert fire_target(24000.0, 4.0) == pytest.approx(600000.0)


def test_project_wealth_without_return_adds_savings():
    assert project_wealth(1000.0, 100.0, 0.0, 2) == [1000.0, 2200.0, 3400.0]


def test_parse_events_groups_by_year_and_ignores_garbage():
    events = parse_events('[{"year": 2, "amount": -500, "label": "Voiture"}, {"year": "x"}, {"year": 2, "amount": 100}]')
    assert events == {2: [{"amount": -500.0, "label": "Voiture"}, {"amount": 100.0, "label": "Événement"}]}
    assert parse_events("pas du json") == {}
    assert parse_events('{"year": 1}') == {}


def test_simulation_without_volatility_is_deterministic():
    args = dict(initial_capital=1000.0, monthly_contribution=100.0, annual_return_pct=0.0, years=2, volatility_pct=0.0,
                inflation_rate_pct=0.0, contribution_indexation_pct=0.0, tax_rate_pct=0.0, tax_deferred=True, events={})
    first = simulate_wealth(**args)
    assert first == simulate_wealth(**args)
    assert [p.total_value for p in first] == [1000.0, 2200.0, 3400.0]
    assert first[-1].total_contributions == 2400.0
