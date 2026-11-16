"""Stock picking face à l'indice de référence : portefeuille fantôme, réglage de la référence, cours manquants."""
import pytest

from app.models.etf_profile import EtfProfile
from app.models.system_setting import SystemSetting
from tests.investissement.test_portfolio import _iso, _prices, _tx, offline_market  # noqa: F401 (fixture)

URL = "/analytics/stock-picking-benchmark"


def _world_profile(db_session):
    profile = EtfProfile(name="Amundi MSCI World", ticker="CW8.PA")
    db_session.add(profile)
    db_session.commit()
    return profile.id


def _cto(client, db_session, name="CTO"):
    """MSCI World (ETF) et LVMH au Point Zéro (−200 j) ; achat d'AAPL, vente de la moitié, dividende."""
    world_id = _world_profile(db_session)
    account_id = client.post("/accounts", json={"name": name, "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    resp = client.post("/holdings/baseline", json={
        "account_id": account_id, "date": _iso(200),
        "holdings": [
            {"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR",
             "etf_profile_id": world_id},
            {"ticker": "MC.PA", "asset_name": "LVMH", "quantity": 2, "buy_price_avg": 500.0, "currency": "EUR"},
        ],
    })
    assert resp.status_code == 200, resp.text
    _prices(db_session, "CW8.PA", (200, 100.0), (120, 100.0), (60, 110.0), (0, 120.0))
    _prices(db_session, "MC.PA", (200, 500.0), (0, 600.0))
    _prices(db_session, "AAPL", (120, 99.0), (60, 120.0), (0, 150.0))
    _tx(client, account_id, "versement", 5000.0, days_ago=150)
    _tx(client, account_id, "achat", 1000.0, days_ago=120, ticker="AAPL", quantity=10, unit_price=99.0, fees=10.0, note="Apple")
    _tx(client, account_id, "vente", 600.0, days_ago=60, ticker="AAPL", quantity=5, unit_price=120.0)
    _tx(client, account_id, "dividende", 20.0, days_ago=30, ticker="AAPL")
    return account_id


def _get(client, **params):
    resp = client.get(URL, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_stock_lines_are_replayed_in_the_largest_etf(client, db_session):
    _cto(client, db_session)
    body = _get(client)

    assert body["benchmark_ticker"] == "CW8.PA"
    assert body["benchmark_name"] == "MSCI World"
    assert body["benchmark_source"] == "largest_etf"
    lines = {line["ticker"]: line for line in body["lines"]}
    assert set(lines) == {"AAPL", "MC.PA"}  # l'ETF n'est pas du stock picking

    aapl = lines["AAPL"]
    assert aapl["invested_eur"] == pytest.approx(1000.0)  # frais compris
    assert aapl["stock_total_eur"] == pytest.approx(5 * 150 + 600 + 20)
    assert aapl["benchmark_proceeds_eur"] == pytest.approx(5 * 110)  # même fraction (½) du fantôme
    assert aapl["benchmark_total_eur"] == pytest.approx(5 * 110 + 5 * 120)
    assert aapl["gap_eur"] == pytest.approx(220.0)

    lvmh = lines["MC.PA"]  # au Point Zéro sans achat connu : départ au prix de revient
    assert lvmh["start_date"] == _iso(200)[:10]
    assert lvmh["invested_eur"] == pytest.approx(1000.0)
    assert lvmh["benchmark_total_eur"] == pytest.approx(1200.0)
    assert lvmh["gap_eur"] == pytest.approx(0.0)  # +20 % des deux côtés

    assert body["gap_eur"] == pytest.approx(220.0)
    assert body["stock_total_eur"] == pytest.approx(1370.0 + 1200.0)
    assert body["start_date"] == _iso(200)[:10]
    assert body["stock_xirr_pct"] is not None and body["benchmark_xirr_pct"] is not None
    assert body["incomplete_tickers"] == []


def test_reference_can_be_overridden_by_query_and_by_setting(client, db_session):
    _cto(client, db_session)
    _prices(db_session, "IWDA.AS", (200, 50.0), (120, 50.0), (60, 50.0), (0, 50.0))

    assert _get(client, benchmark="iwda.as")["benchmark_source"] == "query"
    resp = client.put(f"{URL}/reference", json={"ticker": "IWDA.AS"})
    assert resp.status_code == 200, resp.text
    assert db_session.query(SystemSetting).filter_by(key="benchmark_ticker").one().value == "IWDA.AS"

    body = _get(client)
    assert (body["benchmark_ticker"], body["benchmark_source"]) == ("IWDA.AS", "setting")
    assert body["gap_eur"] == pytest.approx((1370.0 + 1200.0) - (1000.0 + 1000.0))  # référence plate

    assert client.put(f"{URL}/reference", json={"ticker": None}).status_code == 200
    assert _get(client)["benchmark_source"] == "largest_etf"


def test_missing_reference_price_marks_lines_instead_of_counting_zero(client, db_session):
    _cto(client, db_session)
    body = _get(client, benchmark="NOPE.PA")
    assert sorted(body["incomplete_tickers"]) == ["AAPL", "MC.PA"]
    assert all(line["missing_price"] and line["gap_eur"] is None for line in body["lines"])
    assert body["gap_eur"] == 0.0 and body["invested_eur"] == 0.0


def test_distributing_reference_is_flagged(client, db_session):
    account_id = _cto(client, db_session)
    _tx(client, account_id, "dividende", 5.0, days_ago=10, ticker="CW8.PA")  # marque l'ETF distribuant
    body = _get(client)
    assert body["benchmark_distributes"] is True
    assert body["warnings"]


def test_scope_by_account(client, db_session):
    account_id = _cto(client, db_session)
    other = client.post("/accounts", json={"name": "PEA", "type": "investissement", "currency": "EUR", "color": None}).json()["id"]
    assert _get(client, account_id=account_id)["lines"]
    assert _get(client, account_id=other)["lines"] == []
