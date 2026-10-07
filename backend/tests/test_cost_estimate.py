"""Estimation du PRU des lignes du Point Zéro depuis les achats saisis avant sa date."""
from datetime import datetime, timedelta

import pytest

import app.core.currency as currency_mod
import app.core.market_data as market_data
from app.models.portfolio_holding import PortfolioHolding


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(market_data, "_fetch_chart", no_chart)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)
    market_data._QUOTES_CACHE.clear()
    yield
    market_data._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _account(client) -> int:
    return client.post("/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]


def _buy(client, account_id, amount, quantity, unit_price, *, days_ago, ticker="AAPL", price_currency="USD", tx_type="versement", **extra):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": tx_type, "amount": amount, "ticker": ticker,
        "quantity": quantity, "unit_price": unit_price, "price_currency": price_currency, "currency": "EUR", **extra,
    })
    assert resp.status_code == 201, resp.text


def _baseline(client, account_id, quantity, *, days_ago=5, ticker="AAPL", currency="USD"):
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(days_ago),
        "holdings": [{"ticker": ticker, "asset_name": "Apple", "quantity": quantity, "buy_price_avg": None, "currency": currency}],
    })
    assert resp.status_code == 200, resp.text


def test_estimate_is_weighted_average_with_fees_in_position_currency(client):
    account_id = _account(client)
    _buy(client, account_id, 50.0, 1, 100.0, days_ago=100)           # 1 × 100 USD
    _buy(client, account_id, 61.0, 2, 120.0, days_ago=60, fees=2.0)  # 2 × 120 + 2 de frais = 242 USD
    _baseline(client, account_id, 3)

    (est,) = client.get(f"/holdings/estimate-costs?account_id={account_id}").json()
    assert est["estimate"] == pytest.approx((100 + 242) / 3)
    assert est["buys"] == 2 and est["bought_quantity"] == pytest.approx(3)
    assert est["coverage"] == pytest.approx(1.0)
    assert est["current_cost"] is None


def test_estimate_converts_other_currencies_and_ignores_sales_for_the_average(client):
    account_id = _account(client)
    _buy(client, account_id, 100.0, 1, 100.0, days_ago=100, price_currency="EUR")  # 100 EUR = 200 USD (taux 2,0)
    _buy(client, account_id, 80.0, 1, 160.0, days_ago=90)                          # 160 USD
    _buy(client, account_id, 90.0, 1, 180.0, days_ago=80, tx_type="retrait")       # vente : le PRU ne bouge pas
    _baseline(client, account_id, 1)

    (est,) = client.get(f"/holdings/estimate-costs?account_id={account_id}").json()
    assert est["estimate"] == pytest.approx(180.0)  # (200 + 160) / 2
    assert est["sold_quantity"] == pytest.approx(1)
    assert est["coverage"] == pytest.approx(1.0)  # 2 achetées − 1 vendue = 1 détenue


def test_coverage_below_one_when_inventory_exceeds_recorded_purchases(client):
    account_id = _account(client)
    _buy(client, account_id, 50.0, 1, 100.0, days_ago=100)
    _baseline(client, account_id, 4)

    (est,) = client.get(f"/holdings/estimate-costs?account_id={account_id}").json()
    assert est["coverage"] == pytest.approx(0.25)


def test_no_purchase_gives_no_estimate(client):
    account_id = _account(client)
    _baseline(client, account_id, 2)
    (est,) = client.get(f"/holdings/estimate-costs?account_id={account_id}").json()
    assert est["estimate"] is None and est["buys"] == 0


def test_purchases_after_the_baseline_are_not_part_of_the_estimate(client):
    account_id = _account(client)
    _buy(client, account_id, 50.0, 1, 100.0, days_ago=100)
    _baseline(client, account_id, 1, days_ago=50)
    _buy(client, account_id, 80.0, 1, 200.0, days_ago=10)  # rejouée par-dessus l'inventaire
    (est,) = client.get(f"/holdings/estimate-costs?account_id={account_id}").json()
    assert est["estimate"] == pytest.approx(100.0)


def test_apply_costs_updates_baseline_and_rebuilds_positions(client, db_session):
    account_id = _account(client)
    _buy(client, account_id, 50.0, 1, 100.0, days_ago=100)
    _baseline(client, account_id, 1)

    resp = client.post("/holdings/apply-costs", json={"account_id": account_id, "items": [{"ticker": "AAPL", "buy_price_avg": 104.5}]})
    assert resp.status_code == 200, resp.text
    db_session.expire_all()
    holding = db_session.query(PortfolioHolding).filter_by(account_id=account_id, ticker="AAPL").one()
    assert holding.buy_price_avg == pytest.approx(104.5)
    assert holding.cost_basis_eur == pytest.approx(52.25)  # 104,5 USD au taux 2,0

    bad = client.post("/holdings/apply-costs", json={"account_id": account_id, "items": [{"ticker": "ZZZ", "buy_price_avg": 1}]})
    assert bad.status_code == 422


def _legacy_versement(client, account_id, note, original_amount, currency, *, days_ago):
    """Ancien format : montant et libellé seulement, sans titre ni quantité."""
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": "versement", "amount": original_amount,
        "currency": currency, "note": note,
    })
    assert resp.status_code == 201, resp.text


def test_estimate_from_legacy_amounts_matched_by_label(client):
    account_id = _account(client)
    _legacy_versement(client, account_id, "Achat Apple", 10.0, "USD", days_ago=300)
    _legacy_versement(client, account_id, "Apple", 90.0, "USD", days_ago=100)
    _legacy_versement(client, account_id, "Microsoft", 500.0, "USD", days_ago=100)  # autre titre : ignoré
    client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(5),
        "holdings": [
            {"ticker": "AAPL", "asset_name": "Apple Inc.", "quantity": 0.5, "buy_price_avg": None, "currency": "USD"},
            {"ticker": "MSFT", "asset_name": "Microsoft Corporation", "quantity": 1, "buy_price_avg": None, "currency": "USD"},
        ],
    })

    by_ticker = {e["ticker"]: e for e in client.get(f"/holdings/estimate-costs?account_id={account_id}").json()}
    apple = by_ticker["AAPL"]
    assert apple["method"] == "amounts" and apple["amount_only_buys"] == 2
    assert apple["estimate"] == pytest.approx(100.0 / 0.5)  # 100 USD versés pour 0,5 part
    assert apple["coverage"] is None
    assert by_ticker["MSFT"]["estimate"] == pytest.approx(500.0)
