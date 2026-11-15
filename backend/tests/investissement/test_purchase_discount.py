"""Achat décoté (actions salarié) : le cours de référence sépare le gain de décote du gain de marché."""
from datetime import datetime, timedelta

import pytest

import app.integrations.yahoo_finance as yahoo_finance
import app.repositories.investissement.security_prices as security_prices
import app.services.investissement.market.quotes as market_quotes


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    monkeypatch.setattr("app.services.comptes.exchange_rates.get_historical_rate", fake_historical_rate)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _account(client, db_session, price=30.0):
    account_id = client.post("/accounts", json={"name": "AXA", "type": "investissement", "currency": "EUR"}).json()["id"]
    security_prices.store_price(db_session, "CS.PA", datetime.now().date(), price, "EUR")
    db_session.commit()
    return account_id


def _buy(client, account_id, *, quantity, unit_price, reference_price=None, days_ago=30, fees=None):
    body = {
        "account_id": account_id, "date": _iso(days_ago), "type": "achat", "amount": quantity * unit_price + (fees or 0.0),
        "ticker": "CS.PA", "quantity": quantity, "unit_price": unit_price, "price_currency": "EUR",
    }
    if reference_price is not None:
        body["reference_price"] = reference_price
    if fees is not None:
        body["fees"] = fees
    resp = client.post("/investment-transactions", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _portfolio(client, account_id):
    resp = client.get(f"/analytics/portfolio/{account_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_reference_price_is_saved_returned_and_editable(client):
    account_id = client.post("/accounts", json={"name": "AXA", "type": "investissement"}).json()["id"]
    tx = _buy(client, account_id, quantity=50, unit_price=15.0, reference_price=20.0)
    assert tx["reference_price"] == 20.0

    updated = client.patch(f"/investment-transactions/{tx['id']}", json={"reference_price": 21.0}).json()
    assert updated["reference_price"] == 21.0
    cleared = client.patch(f"/investment-transactions/{tx['id']}", json={"reference_price": None}).json()
    assert cleared["reference_price"] is None


def test_gain_splits_into_discount_and_market(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=50, unit_price=15.0, reference_price=20.0)  # décote de 25 %

    p = _portfolio(client, account_id)
    line = p["lines"][0]
    assert line["unrealized_eur"] == pytest.approx(750.0)  # 50 × (30 − 15)
    assert line["discount_eur"] == pytest.approx(250.0)  # 50 × (20 − 15)
    assert line["market_gain_eur"] == pytest.approx(500.0)  # 50 × (30 − 20)
    assert p["discount_eur"] == pytest.approx(250.0)
    assert p["market_gain_eur"] == pytest.approx(500.0)
    assert p["discount_eur"] + p["market_gain_eur"] == pytest.approx(p["unrealized_eur"])


def test_fees_are_not_part_of_the_discount(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=50, unit_price=15.0, reference_price=20.0, fees=10.0)

    line = _portfolio(client, account_id)["lines"][0]
    assert line["discount_eur"] == pytest.approx(250.0)
    assert line["market_gain_eur"] == pytest.approx(line["unrealized_eur"] - 250.0)


def test_discount_follows_the_remaining_quantity_after_a_sale(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=50, unit_price=15.0, reference_price=20.0)
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(5), "type": "vente", "amount": 600.0,
        "ticker": "CS.PA", "quantity": 20, "unit_price": 30.0, "price_currency": "EUR",
    })
    assert resp.status_code == 201, resp.text

    line = _portfolio(client, account_id)["lines"][0]
    assert line["quantity"] == pytest.approx(30.0)
    assert line["discount_eur"] == pytest.approx(150.0)  # 30 × (20 − 15)


def test_plain_purchases_have_no_decomposition(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=10, unit_price=20.0)

    p = _portfolio(client, account_id)
    assert p["lines"][0]["discount_eur"] is None
    assert p["lines"][0]["market_gain_eur"] is None
    assert p["discount_eur"] is None
    assert p["market_gain_eur"] is None


def test_mixed_purchases_only_count_the_discounted_one(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=10, unit_price=20.0, days_ago=60)  # achat normal
    _buy(client, account_id, quantity=50, unit_price=15.0, reference_price=20.0, days_ago=30)

    line = _portfolio(client, account_id)["lines"][0]
    assert line["discount_eur"] == pytest.approx(250.0)
    assert line["market_gain_eur"] == pytest.approx(line["unrealized_eur"] - 250.0)


def test_reference_price_at_or_below_the_paid_price_is_no_discount(client, db_session):
    account_id = _account(client, db_session, price=30.0)
    _buy(client, account_id, quantity=10, unit_price=20.0, reference_price=18.0)

    assert _portfolio(client, account_id)["lines"][0]["discount_eur"] is None


def test_discount_in_foreign_currency_is_converted_at_the_purchase_rate(client, db_session):
    account_id = client.post("/accounts", json={"name": "US", "type": "investissement", "currency": "EUR"}).json()["id"]
    security_prices.store_price(db_session, "CS.PA", datetime.now().date(), 30.0, "USD")
    db_session.commit()
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(30), "type": "achat", "amount": 375.0, "currency": "EUR",
        "ticker": "CS.PA", "quantity": 50, "unit_price": 15.0, "reference_price": 20.0, "price_currency": "USD",
    })
    assert resp.status_code == 201, resp.text

    line = _portfolio(client, account_id)["lines"][0]
    assert line["discount_eur"] == pytest.approx(125.0)  # 250 USD au taux de 2
