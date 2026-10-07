"""Fiscalité : enveloppes, plafonds, dates clés, récap annuel du CTO."""
from datetime import date, datetime, timedelta

import pytest

import app.core.currency as currency_mod
import app.core.market_data as market_data


def _account(client, name="PEA", type_="investissement", **extra) -> dict:
    resp = client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR", "color": None, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_account_keeps_tax_wrapper_and_opening_date(client):
    created = _account(client, tax_wrapper="pea", opened_at="2019-03-15")
    assert created["tax_wrapper"] == "pea"
    assert created["opened_at"] == "2019-03-15"

    resp = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": "cto", "opened_at": "2020-01-02"})
    assert resp.status_code == 200
    assert resp.json()["tax_wrapper"] == "cto"
    assert resp.json()["opened_at"] == "2020-01-02"

    cleared = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": None})
    assert cleared.json()["tax_wrapper"] is None
    assert cleared.json()["opened_at"] == "2020-01-02"


def test_account_rejects_unknown_wrapper(client):
    resp = client.post("/accounts", json={"name": "X", "type": "investissement", "currency": "EUR", "tax_wrapper": "lep"})
    assert resp.status_code == 422


def _versement(client, account_id, amount, *, date_iso, type_="versement"):
    resp = client.post("/investment-transactions", json={"account_id": account_id, "date": date_iso, "type": type_, "amount": amount})
    assert resp.status_code == 201, resp.text


def test_settings_have_defaults_then_persist(client):
    assert client.get("/tax/settings").json() == {"tmi_pct": 30.0, "prior_year_pro_income": 0.0, "household": "single"}
    resp = client.patch("/tax/settings", json={"tmi_pct": 41, "prior_year_pro_income": 52000, "household": "couple"})
    assert resp.status_code == 200
    assert client.get("/tax/settings").json() == {"tmi_pct": 41.0, "prior_year_pro_income": 52000.0, "household": "couple"}


def test_settings_reject_invalid_tmi(client):
    assert client.patch("/tax/settings", json={"tmi_pct": 80}).status_code == 422


def test_overview_empty_without_wrapper(client):
    _account(client, name="Compte sans enveloppe")
    body = client.get("/tax/overview").json()
    assert body["wrappers"] == []


def test_overview_pea_counts_contributions_and_ignores_withdrawals(client):
    pea = _account(client, name="PEA", tax_wrapper="pea", opened_at="2018-01-01")
    _versement(client, pea["id"], 20_000.0, date_iso="2024-02-01T00:00:00")
    _versement(client, pea["id"], 5_000.0, date_iso="2025-02-01T00:00:00", type_="retrait")
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "pea")
    assert card["account_id"] == pea["id"]
    assert card["current"] == 20_000.0
    assert card["remaining"] == pytest.approx(150_000.0 - 20_000.0)
    assert card["milestone_reached"] is True


def test_overview_per_counts_only_current_year_contributions(client):
    per = _account(client, name="PER", tax_wrapper="per", opened_at="2022-01-01")
    year = date.today().year
    _versement(client, per["id"], 2_000.0, date_iso=f"{year}-01-15T00:00:00")
    _versement(client, per["id"], 9_999.0, date_iso=f"{year - 1}-06-15T00:00:00")
    client.patch("/tax/settings", json={"tmi_pct": 30, "prior_year_pro_income": 40_000})
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "per")
    assert card["current"] == 2_000.0
    assert card["estimated_tax_saving"] == pytest.approx(600.0)


def test_overview_livret_a_uses_account_balance(client):
    la = _account(client, name="Livret A", type_="epargne", tax_wrapper="livret_a")
    resp = client.post("/transactions", json={
        "account_id": la["id"], "date": "2026-01-01T00:00:00", "type": "Solde Initial", "merchant": "Solde initial", "amount": 12_000.0,
    })
    assert resp.status_code in (200, 201), resp.text
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "livret_a")
    assert card["current"] == 12_000.0
    assert card["remaining"] == pytest.approx(22_950.0 - 12_000.0)


def test_overview_wrapper_without_opening_date_alerts(client):
    _account(client, name="AV", type_="assurance_vie", tax_wrapper="assurance_vie")
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "assurance_vie")
    assert card["age_years"] is None
    assert any("date d'ouverture" in a.lower() for a in card["alerts"])


def test_tax_routes_require_authentication(db_session):
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as anonymous:
        assert anonymous.get("/tax/overview").status_code in (401, 403)


@pytest.fixture()
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


def _cto_with_sale_and_dividend(client, db_session, *, wrapper="cto"):
    account = _account(client, name="CTO", tax_wrapper=wrapper)
    resp = client.post("/holdings/baseline", json={
        "account_id": account["id"], "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    for days_ago, close in ((200, 100.0), (60, 130.0), (0, 120.0)):
        market_data.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=days_ago)).date(), close, "EUR")
    db_session.commit()
    sale = client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(60), "type": "vente", "amount": 520.0,
        "ticker": "CW8.PA", "quantity": 4, "unit_price": 130.0,
    })
    assert sale.status_code == 201, sale.text
    dividend = client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(30), "type": "dividende", "amount": 35.0,
        "ticker": "CW8.PA", "withholding_tax": 15.0,
    })
    assert dividend.status_code == 201, dividend.text
    return account


def test_annual_report_groups_dividends_and_realized_gains(client, db_session, offline_market):
    account = _cto_with_sale_and_dividend(client, db_session)
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()

    row = next(r for r in report["accounts"] if r["account_id"] == account["id"])
    assert row["realized_eur"] == pytest.approx(120.0)   # 520 − 4 × 100
    assert row["dividends_net_eur"] == pytest.approx(35.0)
    assert row["dividends_gross_eur"] == pytest.approx(50.0)  # net + retenue
    assert report["box_2dc"] == pytest.approx(50.0)
    assert report["box_3vg"] == pytest.approx(120.0)
    assert report["box_3vh"] == 0.0
    assert report["estimated_pfu_eur"] == pytest.approx((50.0 + 120.0) * report["pfu_rate"])


def test_annual_report_ignores_non_cto_accounts(client, db_session, offline_market):
    _cto_with_sale_and_dividend(client, db_session, wrapper="pea")
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()
    assert report["accounts"] == []
    assert report["box_2dc"] == 0.0
    assert report["box_3vg"] == 0.0


def test_annual_report_empty_year_is_all_zero_not_an_error(client, db_session, offline_market):
    _cto_with_sale_and_dividend(client, db_session)
    report = client.get("/tax/annual-report?year=2001")
    assert report.status_code == 200
    body = report.json()
    assert body["box_2dc"] == 0.0 and body["box_3vg"] == 0.0 and body["estimated_pfu_eur"] == 0.0
    assert body["accounts"][0]["realized_eur"] == 0.0


def test_annual_report_loss_goes_to_box_3vh_and_is_not_taxed(client, db_session, offline_market):
    account = _account(client, name="CTO", tax_wrapper="cto")
    client.post("/holdings/baseline", json={
        "account_id": account["id"], "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    market_data.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=60)).date(), 80.0, "EUR")
    db_session.commit()
    client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(60), "type": "vente", "amount": 320.0,
        "ticker": "CW8.PA", "quantity": 4, "unit_price": 80.0,
    })
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()
    assert report["box_3vh"] == pytest.approx(80.0)   # 320 − 400
    assert report["box_3vg"] == 0.0
    assert report["estimated_pfu_eur"] == 0.0


def test_annual_report_flags_sales_without_known_cost(client, db_session, offline_market):
    account = _account(client, name="CTO", tax_wrapper="cto")
    sale = client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(10), "type": "vente", "amount": 500.0,
        "ticker": "ORPH.PA", "quantity": 5, "unit_price": 100.0,
    })
    assert sale.status_code == 201, sale.text
    report = client.get(f"/tax/annual-report?year={datetime.now().year}").json()
    assert report["accounts"][0]["unknown_cost_sales"] == 1
    assert report["box_3vg"] == 0.0
    assert any("coût de revient" in w for w in report["warnings"])
