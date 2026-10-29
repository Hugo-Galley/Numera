"""Rattachement des dividendes et agrégats par position (sans base)."""
from datetime import datetime

from app.domain.dividends import DividendRow, match_dividend_ticker, summarize_by_holding
from app.models.investment_transaction import InvestmentTransaction


def test_match_dividend_ticker_crypto_alias():
    assert match_dividend_ticker("Dividende Bitcoin", [("BTC-EUR", "Bitcoin EUR"), ("CW8.PA", "MSCI World")]) == "BTC-EUR"


def test_match_dividend_ticker_ambiguous_is_none():
    assert match_dividend_ticker("Dividende Amundi", [("CW8.PA", "Amundi World"), ("PAEEM.PA", "Amundi Emerging")]) is None
    assert match_dividend_ticker(None, [("CW8.PA", "Amundi World")]) is None


def test_summarize_by_holding_last_12m():
    today = datetime(2026, 6, 15)
    rows = [
        DividendRow(InvestmentTransaction(account_id=1, ticker="tte.pa", date=datetime(2025, 5, 11)), 10.0, 2.0),
        DividendRow(InvestmentTransaction(account_id=1, ticker="TTE.PA", date=datetime(2026, 6, 5)), 5.0, 1.0),
        DividendRow(InvestmentTransaction(account_id=1, ticker=None, date=datetime(2026, 6, 5)), 3.0, 0.0),
    ]
    summary = summarize_by_holding(rows, today)
    assert list(summary) == [(1, "TTE.PA")]
    item = summary[(1, "TTE.PA")]
    assert (item.total_eur, item.last_12m_eur, item.count, item.last_date.isoformat()) == (15.0, 5.0, 2, "2026-06-05")
    assert rows[0].gross_eur == 12.0
