"""Règle 12 sur les comptes titres : une opération datée après aujourd'hui ne compte qu'à sa date.

Et prix unitaire déduit : recalculé quand le montant, la quantité ou les frais changent.
"""
import asyncio
from datetime import date, datetime, timedelta

import pytest
from freezegun import freeze_time

import app.integrations.currency as currency_mod
import app.integrations.yahoo_finance as yahoo_finance
import app.repositories.investissement.security_prices as security_prices
import app.services.investissement.market.quotes as market_quotes
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _setup(client, db_session) -> int:
    account_id = client.post("/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    for days_ago, close in ((200, 100.0), (100, 110.0), (0, 120.0)):
        security_prices.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=days_ago)).date(), close, "EUR")
    db_session.commit()
    return account_id


def _post(client, account_id, tx_type, amount, days_ago, **extra):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": tx_type, "amount": amount, **extra,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _portfolio(client, account_id):
    resp = client.get(f"/analytics/portfolio/{account_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _snapshot(client, account_id):
    p = _portfolio(client, account_id)
    return p["value"], p["net_invested"], p["cash"], [(line["quantity"], line["avg_cost"]) for line in p["lines"]]


def test_future_versement_and_buy_do_not_count_today(client, db_session):
    account_id = _setup(client, db_session)
    before = _snapshot(client, account_id)
    _post(client, account_id, "versement", 500, -30)
    _post(client, account_id, "achat", 480, -30, ticker="CW8.PA", quantity=4, unit_price=120)
    assert _snapshot(client, account_id) == before
    holding = db_session.query(PortfolioHolding).filter_by(account_id=account_id).one()
    assert holding.quantity == 10


def test_future_operations_count_the_day_after_due_date(client, db_session):
    account_id = _setup(client, db_session)
    before = _snapshot(client, account_id)
    _post(client, account_id, "versement", 500, -30)
    _post(client, account_id, "achat", 480, -30, ticker="CW8.PA", quantity=4, unit_price=120)
    with freeze_time(datetime.now() + timedelta(days=31)):
        security_prices.store_price(db_session, "CW8.PA", date.today(), 120.0, "EUR")
        db_session.commit()
        value, net_invested, cash, lines = _snapshot(client, account_id)
    assert net_invested == before[1] + 500
    assert cash == 20
    assert lines[0][0] == 14
    assert value == 14 * 120 + 20


def test_future_transfer_counterpart_on_securities_account_does_not_count(client, db_session):
    account_id = _setup(client, db_session)
    before = _snapshot(client, account_id)
    db_session.add(Transaction(
        account_id=account_id, date=datetime.now() + timedelta(days=30), month_label="x", type="Entree", merchant="Virement",
        amount=300.0, original_amount=300.0, running_balance=0.0, is_transfer=True,
    ))
    db_session.commit()
    assert _snapshot(client, account_id) == before


def test_investment_transaction_read_exposes_is_upcoming(client, db_session):
    account_id = _setup(client, db_session)
    future = _post(client, account_id, "versement", 500, -30)
    past = _post(client, account_id, "versement", 500, 10)
    assert future["is_upcoming"] is True
    assert past["is_upcoming"] is False
    listed = {t["id"]: t["is_upcoming"] for t in client.get(f"/investment-transactions?account_id={account_id}").json()}
    assert listed == {future["id"]: True, past["id"]: False}


def test_hourly_rebuild_picks_up_operation_that_became_due(client, db_session):
    from app.services.investissement.holdings.rebuild import rebuild_due_holdings

    account_id = _setup(client, db_session)
    _post(client, account_id, "achat", 480, -3, ticker="CW8.PA", quantity=4, unit_price=120)
    assert db_session.query(PortfolioHolding).filter_by(account_id=account_id).one().quantity == 10
    with freeze_time(datetime.now() + timedelta(days=4)):
        asyncio.run(rebuild_due_holdings(db_session))
    db_session.expire_all()
    assert db_session.query(PortfolioHolding).filter_by(account_id=account_id).one().quantity == 14


def test_amount_update_recomputes_derived_unit_price(client, db_session):
    account_id = _setup(client, db_session)
    tx = _post(client, account_id, "achat", 1000, 50, ticker="AAA.PA", quantity=10)
    assert tx["unit_price"] == 100
    resp = client.patch(f"/investment-transactions/{tx['id']}", json={"amount": 1200})
    assert resp.status_code == 200, resp.text
    assert resp.json()["unit_price"] == 120
    holding = next(h for h in client.get(f"/holdings?account_id={account_id}").json() if h["ticker"] == "AAA.PA")
    assert holding["buy_price_avg"] == 120


def test_explicit_unit_price_is_never_overwritten(client, db_session):
    account_id = _setup(client, db_session)
    tx = _post(client, account_id, "achat", 1000, 50, ticker="AAA.PA", quantity=10, unit_price=99)
    resp = client.patch(f"/investment-transactions/{tx['id']}", json={"amount": 1200})
    assert resp.json()["unit_price"] == 99


def test_providing_unit_price_in_patch_makes_it_explicit(client, db_session):
    account_id = _setup(client, db_session)
    tx = _post(client, account_id, "achat", 1000, 50, ticker="AAA.PA", quantity=10)
    resp = client.patch(f"/investment-transactions/{tx['id']}", json={"amount": 1200, "unit_price": 110})
    assert resp.json()["unit_price"] == 110
    resp = client.patch(f"/investment-transactions/{tx['id']}", json={"amount": 1300})
    assert resp.json()["unit_price"] == 110


def test_fees_and_quantity_updates_recompute_derived_price(client, db_session):
    account_id = _setup(client, db_session)
    tx = _post(client, account_id, "achat", 1000, 50, ticker="AAA.PA", quantity=10)
    resp = client.patch(f"/investment-transactions/{tx['id']}", json={"quantity": 8, "fees": 40})
    assert resp.json()["unit_price"] == 120  # (1000 - 40) / 8
    row = db_session.get(InvestmentTransaction, tx["id"])
    assert row.unit_price_derived is True
