"""Allocation avancée : répartition selon ce qui est détenu aujourd'hui, pas selon l'historique des flux."""
from datetime import date, datetime, timedelta

import pytest

import app.integrations.yahoo_finance as yahoo_finance
import app.repositories.investissement.security_prices as security_prices
import app.services.investissement.market.quotes as market_quotes
from app.models.balance_snapshot import BalanceSnapshot


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    monkeypatch.setattr(yahoo_finance, "fetch_chart", no_chart)
    market_quotes._QUOTES_CACHE.clear()
    yield
    market_quotes._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _account(client, **extra) -> int:
    resp = client.post("/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _op(client, account_id, type_, amount, days_ago, **extra):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": type_, "amount": amount, **extra,
    })
    assert resp.status_code == 201, resp.text


def _by(groups: list[dict]) -> dict[str, float]:
    return {g["name"]: g["percentage"] for g in groups}


def test_sold_line_no_longer_weighs_on_allocation_with_positions(client, db_session):
    """Achat Tech 1000 €, revente totale, achat obligations 1000 € → 100 % obligations."""
    account_id = _account(client)
    _op(client, account_id, "versement", 1000.0, 110)
    _op(client, account_id, "achat", 1000.0, 100, ticker="AAA", quantity=10, unit_price=100.0,
        asset_class="Actions", sector="Tech", geographic_zone="USA")
    _op(client, account_id, "vente", 1000.0, 60, ticker="AAA", quantity=10, unit_price=100.0,
        asset_class="Actions", sector="Tech", geographic_zone="USA")
    _op(client, account_id, "achat", 1000.0, 30, ticker="BBB", quantity=10, unit_price=100.0,
        asset_class="Obligations", geographic_zone="Europe")
    for ticker in ("AAA", "BBB"):
        security_prices.store_price(db_session, ticker, date.today(), 100.0, "EUR")
    db_session.commit()

    body = client.get("/analytics/investments-allocation-advanced").json()
    assert _by(body["by_asset_class"]) == {"Obligations": 100.0}
    assert _by(body["by_sector"]) == {"Non classé": 100.0}
    assert _by(body["by_geographic_zone"]) == {"Europe": 100.0}


def test_allocation_follows_position_values_not_amounts_paid(client, db_session):
    account_id = _account(client)
    _op(client, account_id, "versement", 2000.0, 110)
    _op(client, account_id, "achat", 1000.0, 30, ticker="AAA", quantity=10, unit_price=100.0, asset_class="Actions")
    _op(client, account_id, "achat", 1000.0, 30, ticker="BBB", quantity=10, unit_price=100.0, asset_class="Obligations")
    security_prices.store_price(db_session, "AAA", date.today(), 300.0, "EUR")  # AAA a triplé
    security_prices.store_price(db_session, "BBB", date.today(), 100.0, "EUR")
    db_session.commit()

    body = client.get("/analytics/investments-allocation-advanced").json()

    assert _by(body["by_asset_class"]) == {"Actions": 75.0, "Obligations": 25.0}


def test_snapshot_account_counts_net_purchases_only(client, db_session):
    """Compte valorisé par relevé : achats nets des ventes (par titre), dividendes et frais ignorés."""
    account_id = _account(client, valuation_mode="snapshot")
    _op(client, account_id, "achat", 1000.0, 100, ticker="AAA", quantity=10, unit_price=100.0, asset_class="Actions", sector="Tech")
    _op(client, account_id, "vente", 1000.0, 60, ticker="AAA", quantity=10, unit_price=100.0, asset_class="Actions", sector="Tech")
    _op(client, account_id, "achat", 1000.0, 30, ticker="BBB", quantity=10, unit_price=100.0, asset_class="Obligations")
    _op(client, account_id, "dividende", 500.0, 20, ticker="AAA", asset_class="Actions", sector="Tech")
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=1), current_value=1200.0))
    db_session.commit()

    body = client.get("/analytics/investments-allocation-advanced").json()

    assert _by(body["by_asset_class"]) == {"Obligations": 100.0}
