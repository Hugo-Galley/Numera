"""Compte « détenu pour un tiers » (`held_for`) : consultable, mais absent de tous les totaux personnels."""
from datetime import datetime, timedelta

import pytest

import app.integrations.yahoo_finance as yahoo_finance
import app.repositories.investissement.security_prices as security_prices
import app.services.investissement.market.quotes as market_quotes
from app.models.account import Account
from app.repositories.comptes import balances


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return 1.0

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    monkeypatch.setattr("app.services.comptes.exchange_rates.get_historical_rate", fake_historical_rate)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _securities_account(client, db_session, name, *, held_for=None, quantity=10, tax_wrapper=None):
    """Compte titres avec `quantity` actions AXA achetées 20 €, cotées 30 € aujourd'hui."""
    payload = {"name": name, "type": "investissement", "currency": "EUR", "held_for": held_for, "tax_wrapper": tax_wrapper}
    resp = client.post("/accounts", json=payload)
    assert resp.status_code in (200, 201), resp.text
    account_id = resp.json()["id"]
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "CS.PA", "asset_name": "AXA", "quantity": quantity, "buy_price_avg": 20.0, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    for days_ago, close in ((200, 20.0), (0, 30.0)):
        security_prices.store_price(db_session, "CS.PA", (datetime.now() - timedelta(days=days_ago)).date(), close, "EUR")
    db_session.commit()
    return account_id


def _dividend(client, account_id, amount):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(10), "type": "dividende", "amount": amount, "ticker": "CS.PA",
    })
    assert resp.status_code == 201, resp.text


def test_held_for_is_saved_updated_and_cleared(client, db_session):
    created = client.post("/accounts", json={"name": "AXA Maman", "type": "investissement", "held_for": "Maman"}).json()
    assert created["held_for"] == "Maman"
    assert db_session.get(Account, created["id"]).held_for == "Maman"

    cleared = client.patch(f"/accounts/{created['id']}", json={"held_for": None}).json()
    assert cleared["held_for"] is None
    assert client.post("/accounts", json={"name": "CTO", "type": "investissement"}).json()["held_for"] is None


def test_blank_held_for_means_own_account(client):
    created = client.post("/accounts", json={"name": "CTO", "type": "investissement", "held_for": "   "}).json()
    assert created["held_for"] is None


def test_active_accounts_skips_third_party_unless_asked(client, db_session):
    mine = _securities_account(client, db_session, "AXA")
    hers = _securities_account(client, db_session, "AXA Maman", held_for="Maman")

    assert [a.id for a in balances.active_accounts(db_session)] == [mine]
    assert [a.id for a in balances.active_accounts(db_session, include_third_party=True)] == [mine, hers]


def test_net_worth_ignores_third_party_account(client, db_session):
    _securities_account(client, db_session, "AXA", quantity=10)  # 300 €
    _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)  # 1200 €, pas à moi

    allocation = client.get("/analytics/patrimoine-allocation").json()
    assert allocation["net_patrimoine_eur"] == pytest.approx(300.0)
    budget = client.get("/analytics/budget").json()
    assert budget.get("kpis", budget)["solde_actuel"] == pytest.approx(300.0)


def test_accounts_list_still_shows_third_party_account_with_its_value(client, db_session):
    _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)

    account = client.get("/accounts").json()[0]
    assert account["held_for"] == "Maman"
    assert account["balance"] == pytest.approx(1200.0)


def test_portfolio_overview_sums_own_accounts_and_lists_third_party_apart(client, db_session):
    mine = _securities_account(client, db_session, "AXA", quantity=10)
    hers = _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)

    overview = client.get("/analytics/portfolio").json()
    assert overview["value_eur"] == pytest.approx(300.0)
    assert overview["unrealized_eur"] == pytest.approx(100.0)
    assert [a["account_id"] for a in overview["accounts"]] == [mine]
    assert [a["account_id"] for a in overview["third_party_accounts"]] == [hers]
    assert overview["third_party_accounts"][0]["unrealized_eur"] == pytest.approx(400.0)
    assert overview["third_party_accounts"][0]["held_for"] == "Maman"


def test_third_party_portfolio_stays_readable_on_its_own(client, db_session):
    hers = _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)

    portfolio = client.get(f"/analytics/portfolio/{hers}").json()
    assert portfolio["value"] == pytest.approx(1200.0)
    assert portfolio["unrealized_eur"] == pytest.approx(400.0)


def test_investments_overview_ignores_third_party_but_serves_it_when_asked(client, db_session):
    mine = _securities_account(client, db_session, "AXA", quantity=10)
    hers = _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)

    overview = client.get("/analytics/investments").json()
    assert [i["account_id"] for i in overview["items"]] == [mine]
    assert overview["total_current_value"] == pytest.approx(300.0)
    assert client.get(f"/analytics/investments/{hers}").json()["totals"]["current_value"] == pytest.approx(1200.0)
    scoped = client.get("/analytics/investments", params={"account_id": hers}).json()
    assert scoped["total_current_value"] == pytest.approx(1200.0)


def test_dividends_of_third_party_account_are_not_mine(client, db_session):
    mine = _securities_account(client, db_session, "AXA", quantity=10)
    hers = _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)
    _dividend(client, mine, 20.0)
    _dividend(client, hers, 80.0)

    assert client.get("/analytics/dividends").json()["totals"]["net_eur"] == pytest.approx(20.0)
    assert client.get("/analytics/dividends", params={"account_id": hers}).json()["totals"]["net_eur"] == pytest.approx(80.0)


def test_tax_overview_ignores_third_party_account(client, db_session):
    _securities_account(client, db_session, "PEE", tax_wrapper="pee")
    _securities_account(client, db_session, "PEE Maman", held_for="Maman", tax_wrapper="pee")

    cards = client.get("/tax/overview").json()["wrappers"]
    assert [c["account_name"] for c in cards] == ["PEE"]


def test_diversity_scanner_ignores_third_party_positions(client, db_session):
    _securities_account(client, db_session, "AXA", quantity=10)
    _securities_account(client, db_session, "AXA Maman", held_for="Maman", quantity=40)

    scan = client.get("/analytics/diversity-scanner").json()
    assert scan["totals"]["stocks_eur"] == pytest.approx(300.0)
    assert scan["totals"]["wealth_eur"] == pytest.approx(300.0)
