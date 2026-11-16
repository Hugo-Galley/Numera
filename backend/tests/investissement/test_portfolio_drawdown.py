"""Pire baisse (max drawdown) d'un compte titres et de l'ensemble des comptes, sur l'indice neutre des flux."""
import pytest

from tests.investissement.test_portfolio import _day, _iso, _portfolio, _prices, _tx, offline_market  # noqa: F401 (fixture)


def _account_with_dip(client, db_session, name="CTO"):
    account_id = client.post("/accounts", json={"name": name, "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    # 100 → 130 (pic) → 104 (creux, −20 %) → 117 (−10 % sous le pic)
    _prices(db_session, "CW8.PA", (200, 100.0), (150, 130.0), (100, 104.0), (0, 117.0))
    return account_id


def test_account_portfolio_reports_max_drawdown(client, db_session):
    account_id = _account_with_dip(client, db_session)
    dd = _portfolio(client, account_id)["drawdown"]
    assert dd["max_drawdown_pct"] == pytest.approx(-20.0)
    assert dd["peak_date"] >= _day(150).isoformat()
    assert dd["trough_date"] >= _day(100).isoformat()
    assert dd["recovery_date"] is None
    assert dd["current_drawdown_pct"] == pytest.approx(-10.0)


def test_deposit_does_not_hide_the_drawdown(client, db_session):
    account_id = _account_with_dip(client, db_session)
    _tx(client, account_id, "versement", 5000.0, days_ago=90)  # espèces : la valeur brute bondit
    dd = _portfolio(client, account_id)["drawdown"]
    assert dd["max_drawdown_pct"] == pytest.approx(-20.0, abs=0.5)


def test_overview_reports_combined_drawdown(client, db_session):
    _account_with_dip(client, db_session)
    resp = client.get("/analytics/portfolio")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["drawdown"]["max_drawdown_pct"] == pytest.approx(-20.0)
    assert body["accounts"][0]["history"] is None  # la vue globale ne renvoie pas les courbes
