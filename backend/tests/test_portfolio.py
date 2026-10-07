"""Valeur calculée (positions × cours + espèces), plus-values, XIRR/TWR, historique et rapprochement."""
from datetime import date, datetime, timedelta

import pytest

import app.core.currency as currency_mod
import app.core.market_data as market_data
from app.core.portfolio import twr, xirr
from app.models.balance_snapshot import BalanceSnapshot


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


def _day(days_ago: int) -> date:
    return (datetime.now() - timedelta(days=days_ago)).date()


def _prices(db_session, ticker, *points, currency="EUR"):
    """points : (jours en arrière, cours)."""
    for days_ago, close in points:
        market_data.store_price(db_session, ticker, _day(days_ago), close, currency)
    db_session.commit()


def _setup(client, db_session, *, quantity=10, pru=100.0, account_type="investissement"):
    account_id = client.post(
        "/accounts", json={"name": "CTO", "type": account_type, "currency": "EUR", "color": None}
    ).json()["id"]
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": quantity, "buy_price_avg": pru, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    _prices(db_session, "CW8.PA", (200, 100.0), (100, 110.0), (50, 115.0), (0, 120.0))
    return account_id


def _tx(client, account_id, tx_type, amount, *, days_ago=100, expected=201, **extra):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": tx_type, "amount": amount, **extra,
    })
    assert resp.status_code == expected, resp.text
    return resp.json()


def _portfolio(client, account_id):
    resp = client.get(f"/analytics/portfolio/{account_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


# ─── Fonctions pures ────────────────────────────────────────────────────────

def test_xirr_one_year_ten_percent():
    flows = [(date(2025, 1, 1), -100.0), (date(2026, 1, 1), 110.0)]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-4)


def test_xirr_needs_both_signs():
    assert xirr([(date(2025, 1, 1), -100.0)]) is None
    assert xirr([(date(2025, 1, 1), 100.0), (date(2025, 6, 1), 50.0)]) is None


def test_xirr_weights_late_deposit_less_than_simple_return():
    # 100 investis un an, 100 de plus à mi-parcours, 230 à la fin
    flows = [(date(2025, 1, 1), -100.0), (date(2025, 7, 2), -100.0), (date(2026, 1, 1), 230.0)]
    rate = xirr(flows)
    assert 0.18 < rate < 0.40


def test_twr_ignores_deposit_timing():
    # 100 → 110 (+10 %), puis dépôt de 100 et valeur 220 : avant dépôt 120 sur 110 (+9,09 %) ⇒ +20 % cumulé
    points = [(date(2025, 1, 1), 100.0, 0.0), (date(2025, 2, 1), 110.0, 0.0), (date(2025, 3, 1), 220.0, 100.0)]
    assert twr(points) == pytest.approx(0.20, abs=1e-6)


# ─── Valeur et plus-value latente ───────────────────────────────────────────

def test_value_is_positions_times_price_and_unrealized_gain(client, db_session):
    account_id = _setup(client, db_session)
    p = _portfolio(client, account_id)

    assert p["value_source"] == "positions"
    assert p["value"] == pytest.approx(1200.0)  # 10 × 120
    assert p["cash"] == pytest.approx(0.0)
    assert p["net_invested"] == pytest.approx(1000.0)  # inventaire valorisé au cours du Point Zéro
    assert p["gain"] == pytest.approx(200.0)
    assert p["unrealized_eur"] == pytest.approx(200.0)
    assert p["unrealized_pct"] == pytest.approx(20.0)
    assert p["xirr_pct"] > 0
    line = p["lines"][0]
    assert line["ticker"] == "CW8.PA" and line["avg_cost"] == pytest.approx(100.0)
    assert line["price_stale"] is True  # Yahoo hors ligne : dernier cours stocké


def test_buy_moves_cash_into_the_position(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "versement", 500.0)
    _tx(client, account_id, "achat", 220.0, days_ago=99, ticker="CW8.PA", quantity=2, unit_price=110.0)
    p = _portfolio(client, account_id)

    assert p["cash"] == pytest.approx(280.0)
    assert p["value"] == pytest.approx(12 * 120 + 280)
    assert p["net_invested"] == pytest.approx(1500.0)
    assert p["gain"] == pytest.approx(220.0)  # l'achat lui-même ne crée ni ne détruit de valeur


def test_legacy_versement_with_security_leaves_cash_untouched(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "versement", 220.0, days_ago=99, ticker="CW8.PA", quantity=2, unit_price=110.0)
    p = _portfolio(client, account_id)

    assert p["cash"] == pytest.approx(0.0)
    assert p["net_invested"] == pytest.approx(1220.0)
    assert p["value"] == pytest.approx(1440.0)


def test_dividend_feeds_cash_and_value_not_net_invested(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "dividende", 50.0, ticker="CW8.PA")
    p = _portfolio(client, account_id)

    assert p["cash"] == pytest.approx(50.0)
    assert p["net_invested"] == pytest.approx(1000.0)
    assert p["value"] == pytest.approx(1250.0)
    assert p["dividends_eur"] == pytest.approx(50.0)
    assert p["gain"] == pytest.approx(250.0)


def test_reinvested_dividend_does_not_change_cash(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "dividende", 55.0, ticker="CW8.PA", quantity=0.5, reinvested=True)
    p = _portfolio(client, account_id)

    assert p["cash"] == pytest.approx(0.0)
    assert p["lines"][0]["quantity"] == pytest.approx(10.5)
    assert p["net_invested"] == pytest.approx(1000.0)
    assert p["gain"] == pytest.approx(10.5 * 120 - 1000.0)


def test_fees_reduce_value_and_are_totalled(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "versement", 300.0)
    _tx(client, account_id, "frais", 12.0, days_ago=90)
    _tx(client, account_id, "achat", 221.0, days_ago=80, ticker="CW8.PA", quantity=2, unit_price=110.0, fees=1.0)
    p = _portfolio(client, account_id)

    assert p["fees_eur"] == pytest.approx(13.0)  # 12 de frais de tenue + 1 de courtage
    assert p["cash"] == pytest.approx(300 - 12 - 221)


# ─── Plus-value réalisée ────────────────────────────────────────────────────

def test_realized_gain_uses_cost_basis_and_groups_by_year(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "vente", 520.0, days_ago=60, ticker="CW8.PA", quantity=4, unit_price=130.0)
    p = _portfolio(client, account_id)

    assert p["realized_eur"] == pytest.approx(120.0)  # 520 − 4 × 100
    year = (datetime.now() - timedelta(days=60)).year
    assert p["realized_by_year"] == [{"year": year, "realized_eur": pytest.approx(120.0), "proceeds_eur": pytest.approx(520.0), "sales": 1}]
    assert p["cash"] == pytest.approx(520.0)
    assert p["value"] == pytest.approx(6 * 120 + 520)
    assert p["unrealized_eur"] == pytest.approx(6 * 120 - 600)


def test_realized_gain_subtracts_sale_fees(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "vente", 515.0, days_ago=60, ticker="CW8.PA", quantity=4, unit_price=130.0, fees=5.0)
    assert _portfolio(client, account_id)["realized_eur"] == pytest.approx(115.0)


# ─── Historique, rapprochement et branchements ──────────────────────────────

def test_history_is_rebuilt_from_stored_prices(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "versement", 100.0)  # force un point de courbe au jour -100
    p = _portfolio(client, account_id)

    history = p["history"]
    assert history[0]["date"][:10] == _day(200).isoformat()
    assert history[0]["value"] == pytest.approx(1000.0)
    assert history[-1]["value"] == pytest.approx(1300.0)  # 10 × 120 + 100 d'espèces
    values = {pt["date"][:10]: pt for pt in history}
    assert values[_day(100).isoformat()]["value"] == pytest.approx(1200.0)  # 10 × 110 + 100
    assert values[_day(100).isoformat()]["net_invested"] == pytest.approx(1100.0)
    # TWR : +10 % avant le dépôt, puis +4,17 % et +4 % (les espèces ne rapportent rien)
    assert p["twr_pct"] == pytest.approx(19.2, abs=0.3)


def test_reconciliation_flags_gap_above_two_percent(client, db_session):
    account_id = _setup(client, db_session)
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=50), current_value=1300.0))
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=100), current_value=1100.0))
    db_session.commit()
    rec = _portfolio(client, account_id)["reconciliation"]

    by_day = {r["date"][:10]: r for r in rec}
    assert by_day[_day(100).isoformat()]["flagged"] is False
    far = by_day[_day(50).isoformat()]
    assert far["computed_value"] == pytest.approx(1150.0)
    assert far["gap"] == pytest.approx(-150.0)
    assert far["flagged"] is True

    actions = client.get("/analytics/actions").json()["actions"]
    assert any(a["id"].startswith(f"reconciliation-gap-{account_id}-") for a in actions)


def test_investments_endpoints_switch_to_computed_value(client, db_session):
    account_id = _setup(client, db_session)
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=10), current_value=900.0))
    db_session.commit()

    overview = client.get("/analytics/investments").json()
    item = next(i for i in overview["items"] if i["account_id"] == account_id)
    assert item["value_source"] == "positions"
    assert item["current_value"] == pytest.approx(1200.0)
    assert item["gain_eur"] == pytest.approx(200.0)

    detail = client.get(f"/analytics/investments/{account_id}").json()
    assert detail["totals"]["value_source"] == "positions"
    assert detail["totals"]["current_value"] == pytest.approx(1200.0)
    assert detail["totals"]["snapshot_value"] == pytest.approx(900.0)

    series = client.get(f"/analytics/investments/{account_id}/performance-history").json()
    assert series["value_source"] == "positions"
    assert series["items"][-1]["current_value"] == pytest.approx(1200.0)


def test_overview_aggregates_value_realized_and_dividends(client, db_session):
    account_id = _setup(client, db_session)
    _tx(client, account_id, "vente", 520.0, days_ago=60, ticker="CW8.PA", quantity=4, unit_price=130.0)
    _tx(client, account_id, "dividende", 20.0, days_ago=30, ticker="CW8.PA")
    resp = client.get("/analytics/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["value_eur"] == pytest.approx(6 * 120 + 520 + 20)
    assert data["realized_eur"] == pytest.approx(120.0)
    assert data["dividends_eur"] == pytest.approx(20.0)
    assert len(data["accounts"]) == 1
    assert data["xirr_pct"] is not None


def test_assurance_vie_stays_valued_by_snapshot(client, db_session):
    account_id = _setup(client, db_session, account_type="assurance_vie")
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=5), current_value=5000.0))
    db_session.commit()

    assert _portfolio(client, account_id)["value_source"] == "snapshot"
    item = next(i for i in client.get("/analytics/investments").json()["items"] if i["account_id"] == account_id)
    assert item["value_source"] == "snapshot"
    assert item["current_value"] == pytest.approx(5000.0)


def test_unpriced_line_is_valued_at_cost_with_a_warning(client, db_session):
    account_id = client.post("/accounts", json={"name": "PEA", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(30),
        "holdings": [{"ticker": "ZZZ.PA", "asset_name": "Inconnu", "quantity": 5, "buy_price_avg": 20.0, "currency": "EUR"}],
    })
    p = _portfolio(client, account_id)

    assert p["value"] == pytest.approx(100.0)  # jamais 0 : coût de revient
    assert p["lines"][0]["priced"] is False
    assert p["history"] is None
    assert any("ZZZ.PA" in w for w in p["warnings"])


def test_account_without_positions_is_not_overridden(client, db_session):
    account_id = client.post("/accounts", json={"name": "CTO vide", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now(), current_value=700.0))
    db_session.commit()
    item = next(i for i in client.get("/analytics/investments").json()["items"] if i["account_id"] == account_id)
    assert item["value_source"] == "snapshot"
    assert item["current_value"] == pytest.approx(700.0)


def test_usd_line_splits_unrealized_gain_into_price_and_currency_effect(client, db_session, monkeypatch):
    async def current_rates(base="EUR"):
        return {"EUR": 1.0, "USD": 1.6}  # le dollar a monté depuis l'achat (taux historique : 2,0)

    monkeypatch.setattr(market_data, "get_exchange_rates", current_rates)
    monkeypatch.setattr(currency_mod, "get_exchange_rates", current_rates)
    import app.core.portfolio as portfolio_mod
    monkeypatch.setattr(portfolio_mod, "get_exchange_rates", current_rates)

    account_id = client.post("/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [{"ticker": "AAPL", "asset_name": "Apple", "quantity": 10, "buy_price_avg": 100.0, "currency": "USD"}],
    })
    _prices(db_session, "AAPL", (200, 100.0), (0, 150.0), currency="USD")
    p = _portfolio(client, account_id)

    line = p["lines"][0]
    assert line["cost_eur"] == pytest.approx(500.0)  # 1000 USD au taux d'achat 2,0
    assert line["value_eur"] == pytest.approx(937.5)  # 1500 USD au taux actuel 1,6
    assert line["unrealized_eur"] == pytest.approx(437.5)
    assert line["unrealized_local"] == pytest.approx(500.0)  # (150 − 100) × 10 en USD
    assert line["fx_effect_eur"] == pytest.approx(125.0)  # 437,5 − 500/1,6
    assert p["fx_effect_eur"] == pytest.approx(125.0)


def test_allocation_endpoint_uses_computed_value(client, db_session):
    account_id = _setup(client, db_session)
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=10), current_value=900.0))
    db_session.commit()
    data = client.get("/analytics/investments-allocation").json()
    item = next(i for i in data["items"] if i["account_id"] == account_id)
    assert item["value_source"] == "positions"
    assert item["current_value"] == pytest.approx(1200.0)
    assert data["total_current_value"] == pytest.approx(1200.0)


def test_gain_is_measured_since_inception_not_since_the_positions_baseline(client, db_session):
    """Point Zéro des positions posé après coup : les versements et relevés antérieurs restent comptés."""
    account_id = client.post("/accounts", json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    _tx(client, account_id, "versement", 400.0, days_ago=120, ticker="CW8.PA", quantity=4, unit_price=100.0)
    _tx(client, account_id, "versement", 330.0, days_ago=60, ticker="CW8.PA", quantity=3, unit_price=110.0)
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime.now() - timedelta(days=60), current_value=720.0))
    db_session.commit()
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(5),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 7, "buy_price_avg": None, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    _prices(db_session, "CW8.PA", (120, 100.0), (60, 110.0), (5, 118.0), (0, 120.0))
    p = _portfolio(client, account_id)

    assert p["net_invested"] == pytest.approx(730.0)  # 400 + 330, pas la valeur du jour du Point Zéro
    assert p["value"] == pytest.approx(7 * 120)
    assert p["gain"] == pytest.approx(110.0)
    assert p["xirr_pct"] is not None
    # la courbe reprend les relevés antérieurs au Point Zéro
    first = p["history"][0]
    assert first["date"][:10] == _day(60).isoformat()
    assert first["value"] == pytest.approx(720.0)
    assert first["net_invested"] == pytest.approx(730.0)
