"""Coût de revient EUR d'une ligne d'inventaire en devise : saisi (prioritaire) ou converti au taux du Point Zéro (avertissement)."""
from datetime import date, datetime

import pytest

import app.integrations.yahoo_finance as yahoo_finance
import app.services.investissement.market.quotes as market_quotes

YEAR = date.today().year - 1


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]  # 1 EUR = 2 USD

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    monkeypatch.setattr("app.services.comptes.exchange_rates.get_historical_rate", fake_historical_rate)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _at(month: int, day: int) -> str:
    return datetime(YEAR, month, day, 12, 0, 0).isoformat()


def _cto(client, *, currency="USD", **line) -> int:
    account_id = client.post("/accounts", json={
        "name": "CTO", "type": "investissement", "currency": "EUR", "color": None, "tax_wrapper": "cto",
    }).json()["id"]
    item = {"ticker": "AAPL", "asset_name": "Apple", "quantity": 10, "buy_price_avg": 100.0, "currency": currency, **line}
    resp = client.post("/holdings/baseline", json={"account_id": account_id, "date": _at(1, 5), "holdings": [item]})
    assert resp.status_code == 200, resp.text
    return account_id


def _sell(client, account_id, *, ticker="AAPL", quantity=4, unit_price=150.0, price_currency="USD"):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _at(6, 15), "type": "vente", "amount": quantity * unit_price / 2,
        "ticker": ticker, "quantity": quantity, "unit_price": unit_price, "price_currency": price_currency,
    })
    assert resp.status_code == 201, resp.text


def _report(client) -> dict:
    return client.get(f"/tax/annual-report?year={YEAR}").json()


def test_entered_eur_cost_basis_overrides_the_point_zero_conversion(client):
    account_id = _cto(client, cost_basis_eur=800.0)  # converti au taux du jour : 1000 $ = 500 €
    _sell(client, account_id)  # 4 × 150 $ = 600 $ = 300 €

    row = _report(client)["accounts"][0]

    assert row["realized_eur"] == pytest.approx(300.0 - 800.0 * 4 / 10)
    assert not any("devise" in w for w in _report(client)["warnings"])


def test_foreign_currency_baseline_without_eur_cost_warns(client):
    account_id = _cto(client)
    _sell(client, account_id)

    report = _report(client)

    assert report["accounts"][0]["realized_eur"] == pytest.approx(300.0 - 500.0 * 4 / 10)
    assert any("CTO" in w and "devise" in w and "AAPL" in w for w in report["warnings"])


def test_eur_baseline_and_purchases_after_point_zero_do_not_warn(client):
    account_id = _cto(client, currency="EUR", ticker="CW8.PA", asset_name="MSCI World")
    _sell(client, account_id, ticker="CW8.PA", unit_price=150.0, price_currency="EUR")

    assert not any("devise" in w for w in _report(client)["warnings"])


def test_resaving_the_inventory_without_the_field_keeps_the_entered_cost(client):
    account_id = _cto(client, cost_basis_eur=800.0)
    item = {"ticker": "AAPL", "asset_name": "Apple", "quantity": 10, "buy_price_avg": 100.0, "currency": "USD"}
    resp = client.post("/holdings/baseline", json={"account_id": account_id, "date": _at(1, 5), "holdings": [item]})
    assert resp.status_code == 200
    _sell(client, account_id)

    assert _report(client)["accounts"][0]["realized_eur"] == pytest.approx(300.0 - 320.0)


def test_cost_basis_can_be_cleared_explicitly(client):
    account_id = _cto(client, cost_basis_eur=800.0)
    item = {"ticker": "AAPL", "asset_name": "Apple", "quantity": 10, "buy_price_avg": 100.0, "currency": "USD", "cost_basis_eur": None}
    client.post("/holdings/baseline", json={"account_id": account_id, "date": _at(1, 5), "holdings": [item]})
    _sell(client, account_id)

    assert _report(client)["accounts"][0]["realized_eur"] == pytest.approx(300.0 - 200.0)


def test_holding_update_sets_the_eur_cost_basis(client):
    account_id = _cto(client)
    holding = client.get("/holdings").json()[0]

    resp = client.put(f"/holdings/{holding['id']}", json={"cost_basis_eur": 900.0})

    assert resp.status_code == 200, resp.text
    assert resp.json()["cost_basis_eur"] == pytest.approx(900.0)
    _sell(client, account_id)
    assert _report(client)["accounts"][0]["realized_eur"] == pytest.approx(300.0 - 360.0)
