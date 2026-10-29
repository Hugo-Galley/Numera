"""Calculs purs des rapports : écarts, blocs money-flow, graphe Sankey, projection de trésorerie."""
from datetime import datetime
from types import SimpleNamespace

from app.domain.reports import calc_diff, money_flow_block, sankey_graph, simulate_cashflow


def test_calc_diff_with_negative_values():
    assert calc_diff(200.0, -500.0) == (700.0, 140.0)
    assert calc_diff(-100.0, -200.0) == (100.0, 50.0)
    assert calc_diff(-300.0, -200.0) == (-100.0, -50.0)
    assert calc_diff(10.0, 0.0) == (10.0, 0.0)


def test_money_flow_block_share_of_income_and_change():
    block = money_flow_block(300.0, 200.0, 1200.0)
    assert (block.amount, block.percentage, block.diff_prev_month, block.diff_prev_month_pct) == (300.0, 25.0, 100.0, 50.0)
    assert money_flow_block(5.0, 0.0, 0.0).percentage == 0


def test_sankey_graph_balances_budget_node_with_savings():
    food = SimpleNamespace(id=1, name="Courses", color="#f00", group="Vie courante")
    rent = SimpleNamespace(id=2, name="Loyer", color="#00f", group=None)
    graph = sankey_graph(
        income_sources=[{"name": "Salaire", "total": 2000.0, "color": "#0f0"}],
        total_income=2000.0,
        invest_total=300.0,
        cat_expenses={1: {"obj": food, "total": 400.0}, 2: {"obj": rent, "total": 800.0}},
    )
    names = [n["name"] for n in graph["nodes"]]
    assert names == ["Budget", "Salaire", "Investissements", "Épargne", "Vie courante", "Courses", "Loyer"]
    out_of_budget = sum(link["value"] for link in graph["links"] if link["source"] == 0)
    assert out_of_budget == 2000.0
    assert graph["nodes"][5]["category_id"] == 1


def test_sankey_graph_adds_deficit_when_spending_exceeds_income():
    rent = SimpleNamespace(id=2, name="Loyer", color="#00f", group=None)
    graph = sankey_graph([{"name": "Salaire", "total": 500.0, "color": "#0f0"}], 500.0, 0.0, {2: {"obj": rent, "total": 800.0}})
    deficit = next(link for link in graph["links"] if graph["nodes"][link["source"]]["name"] == "Déficit / Trésorerie")
    assert deficit["value"] == 300.0


def test_simulate_cashflow_tracks_low_point():
    events = [
        SimpleNamespace(date="2026-06-16T00:00:00", amount=700.0, is_income=False),
        SimpleNamespace(date="2026-06-17T00:00:00", amount=2000.0, is_income=True),
    ]
    points, final, low, low_date = simulate_cashflow(events, 500.0, datetime(2026, 6, 15, 10), datetime(2026, 6, 18, 10))
    assert [p.balance for p in points] == [500.0, -200.0, 1800.0, 1800.0]
    assert (final, low, low_date) == (1800.0, -200.0, "2026-06-16")
