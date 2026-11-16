"""Portefeuille fantôme : chaque achat d'action rejoué dans l'indice de référence (sans base)."""
from datetime import date

import pytest

from app.domain.benchmark import LineEvent, compare_line, compare_lines

TODAY = date(2026, 1, 1)


def test_buy_is_replayed_in_the_benchmark_same_day_same_amount():
    line = compare_line("AAPL", [LineEvent(date(2025, 1, 1), "buy", 1000.0, benchmark_price_eur=100.0)],
                        value_eur=1500.0, benchmark_price_eur=120.0, today=TODAY)
    assert line["start_date"] == date(2025, 1, 1)
    assert line["invested_eur"] == pytest.approx(1000.0)
    assert line["stock_total_eur"] == pytest.approx(1500.0)
    assert line["benchmark_total_eur"] == pytest.approx(1200.0)  # 10 parts fantômes × 120
    assert line["gap_eur"] == pytest.approx(300.0)
    assert line["stock_xirr_pct"] == pytest.approx(50.0, abs=0.1)
    assert line["benchmark_xirr_pct"] == pytest.approx(20.0, abs=0.1)
    assert line["missing_price"] is False


def test_sale_sells_the_same_fraction_of_the_ghost_and_dividends_count_on_stock_side_only():
    events = [
        LineEvent(date(2025, 1, 1), "buy", 1000.0, benchmark_price_eur=100.0),
        LineEvent(date(2025, 6, 1), "dividend", 30.0),
        LineEvent(date(2025, 7, 1), "sell", 700.0, fraction=0.5, benchmark_price_eur=110.0),
    ]
    line = compare_line("AAPL", events, value_eur=800.0, benchmark_price_eur=120.0, today=TODAY)
    assert line["stock_proceeds_eur"] == pytest.approx(700.0)
    assert line["dividends_eur"] == pytest.approx(30.0)
    assert line["stock_total_eur"] == pytest.approx(1530.0)
    assert line["benchmark_proceeds_eur"] == pytest.approx(550.0)  # 5 parts × 110
    assert line["benchmark_value_eur"] == pytest.approx(600.0)  # 5 parts × 120
    assert line["benchmark_total_eur"] == pytest.approx(1150.0)
    assert line["gap_eur"] == pytest.approx(380.0)


def test_missing_benchmark_price_marks_the_line_instead_of_counting_zero():
    events = [LineEvent(date(2025, 1, 1), "buy", 1000.0, benchmark_price_eur=None)]
    line = compare_line("AAPL", events, value_eur=1500.0, benchmark_price_eur=120.0, today=TODAY)
    assert line["missing_price"] is True
    assert line["benchmark_total_eur"] is None and line["gap_eur"] is None
    assert line["stock_total_eur"] == pytest.approx(1500.0)


def test_missing_stock_price_marks_the_line():
    line = compare_line("AAPL", [LineEvent(date(2025, 1, 1), "buy", 1000.0, benchmark_price_eur=100.0)],
                        value_eur=None, benchmark_price_eur=120.0, today=TODAY)
    assert line["missing_price"] is True and line["gap_eur"] is None and line["stock_total_eur"] is None


def test_totals_add_complete_lines_and_list_incomplete_ones():
    a = compare_line("AAPL", [LineEvent(date(2025, 1, 1), "buy", 1000.0, benchmark_price_eur=100.0)],
                     value_eur=1500.0, benchmark_price_eur=120.0, today=TODAY)
    b = compare_line("MSFT", [LineEvent(date(2025, 7, 1), "buy", 500.0, benchmark_price_eur=100.0)],
                     value_eur=400.0, benchmark_price_eur=120.0, today=TODAY)
    c = compare_line("TSLA", [LineEvent(date(2025, 1, 1), "buy", 500.0, benchmark_price_eur=None)],
                     value_eur=400.0, benchmark_price_eur=120.0, today=TODAY)
    totals = compare_lines([a, b, c], TODAY)
    assert totals["invested_eur"] == pytest.approx(1500.0)
    assert totals["stock_total_eur"] == pytest.approx(1900.0)
    assert totals["benchmark_total_eur"] == pytest.approx(1800.0)
    assert totals["gap_eur"] == pytest.approx(100.0)
    assert totals["start_date"] == date(2025, 1, 1)
    assert totals["incomplete_tickers"] == ["TSLA"]
    assert totals["stock_xirr_pct"] is not None and totals["benchmark_xirr_pct"] is not None


def test_no_xirr_on_a_too_short_period():
    line = compare_line("AAPL", [LineEvent(date(2025, 12, 28), "buy", 1000.0, benchmark_price_eur=100.0)],
                        value_eur=1010.0, benchmark_price_eur=100.0, today=TODAY)
    assert line["stock_xirr_pct"] is None and line["benchmark_xirr_pct"] is None


def test_unknown_amount_marks_the_line():
    line = compare_line("MC.PA", [LineEvent(date(2025, 1, 1), "buy", None, benchmark_price_eur=100.0)],
                        value_eur=1200.0, benchmark_price_eur=120.0, today=TODAY)
    assert line["missing_price"] is True and line["gap_eur"] is None


def test_line_events_skip_etfs_and_reinvested_dividends():
    from datetime import datetime

    from app.domain.benchmark import stock_line_events
    from app.domain.holdings import Position, Replay, Trade

    zero = datetime(2025, 1, 1)
    replay = Replay(
        positions={}, realized=[], baseline_date=zero, quantity_events=[],
        baseline={"MC.PA": Position("MC.PA", "EUR", quantity=2, cost_eur=1000.0, cutoff=zero),
                  "CW8.PA": Position("CW8.PA", "EUR", quantity=10, cost_eur=1000.0, cutoff=zero)},
        trades=[
            Trade(datetime(2025, 3, 1), "MC.PA", "buy", 1, 2, 550.0),
            Trade(datetime(2025, 4, 1), "MC.PA", "buy", 0.1, 3, 50.0, reinvested=True),
            Trade(datetime(2025, 5, 1), "MC.PA", "sell", 1.55, 3.1, 900.0),
        ],
    )
    dividends = [(date(2025, 4, 1), "MC.PA", 50.0, True), (date(2025, 6, 1), "MC.PA", 12.0, False), (date(2024, 6, 1), "MC.PA", 9.0, False)]
    events = stock_line_events(replay, dividends, excluded={"CW8.PA"})
    assert set(events) == {"MC.PA"}
    kinds = [(e.day, e.kind, e.amount_eur, round(e.fraction, 3)) for e in events["MC.PA"]]
    assert kinds == [
        (date(2025, 1, 1), "buy", 1000.0, 0.0), (date(2025, 3, 1), "buy", 550.0, 0.0),
        (date(2025, 5, 1), "sell", 900.0, 0.5), (date(2025, 6, 1), "dividend", 12.0, 0.0),
    ]
