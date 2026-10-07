"""Dividendes : rattachement à un titre, réinvestissement, agrégats EUR, rappels du Centre d'Actions."""
from datetime import datetime, timedelta

import pytest

import app.core.currency as currency_mod
import app.core.market_data as market_data
from app.core.dividends import match_dividend_ticker
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding

HOLDINGS = [
    ("AAPL", "Apple Inc."),
    ("TTE", "TotalEnergies SE"),
    ("BLK", "BlackRock, Inc."),
    ("HO.PA", "THALES"),
    ("MSFT", "Microsoft Corporation"),
    ("CSCO", "Cisco Systems, Inc."),
]


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


def _account(client, name="CTO") -> int:
    resp = client.post("/accounts", json={"name": name, "type": "investissement", "currency": "EUR", "color": None})
    assert resp.status_code == 201
    return resp.json()["id"]


def _baseline(client, account_id, *lines, days_ago=200):
    items = [
        {"ticker": t, "asset_name": n, "quantity": q, "buy_price_avg": p, "currency": "EUR"}
        for t, n, q, p in lines
    ]
    resp = client.post("/holdings/baseline", json={"account_id": account_id, "date": _iso(days_ago), "holdings": items})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _dividend(client, account_id, amount, *, days_ago=100, ticker="CW8.PA", expected=201, **extra):
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(days_ago), "type": "dividende", "amount": amount,
        "ticker": ticker, **extra,
    })
    assert resp.status_code == expected, resp.text
    return resp.json()


def _holding(db_session, account_id, ticker="CW8.PA"):
    db_session.expire_all()
    return db_session.query(PortfolioHolding).filter_by(account_id=account_id, ticker=ticker).first()


# ─── Rattachement d'un libellé à un titre ───────────────────────────────────

@pytest.mark.parametrize("note,expected", [
    ("Dividende Apple", "AAPL"),
    ("Apple", "AAPL"),
    ("Total", "TTE"),
    ("Dividende Total Energie", "TTE"),
    ("Dividende Blackrock", "BLK"),
    ("Dividende MSFT", "MSFT"),
    ("Microsoft", "MSFT"),
    ("Thales", "HO.PA"),
    ("Dividende Cisco", "CSCO"),
    ("Correction Impot", None),
    ("", None),
    (None, None),
])
def test_match_dividend_ticker(note, expected):
    assert match_dividend_ticker(note, HOLDINGS) == expected


def test_match_dividend_ticker_refuses_ambiguity():
    assert match_dividend_ticker("Dividende Apple", [("AAPL", "Apple Inc."), ("APLE", "Apple Hospitality REIT")]) is None


# ─── Saisie ─────────────────────────────────────────────────────────────────

def test_dividend_requires_a_security_and_keeps_position_unchanged(client, db_session):
    account_id = _account(client)
    _baseline(client, account_id, ("CW8.PA", "Amundi MSCI World", 10, 100.0))

    _dividend(client, account_id, 12.0, ticker=None, expected=422)

    tx = _dividend(client, account_id, 12.0, withholding_tax=2.0)
    assert tx["withholding_tax"] == pytest.approx(2.0)
    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(10)
    assert h.buy_price_avg == pytest.approx(100.0)
    assert h.pays_dividends is True  # un dividende saisi marque le titre comme distribuant


def test_withholding_and_reinvestment_only_apply_to_dividends(client):
    account_id = _account(client)
    resp = client.post("/investment-transactions", json={
        "account_id": account_id, "date": _iso(10), "type": "versement", "amount": 100.0, "withholding_tax": 5.0,
    })
    assert resp.status_code == 422
    # Réinvestir exige les parts reçues
    _dividend(client, account_id, 45.0, reinvested=True, expected=422)


def test_reinvested_dividend_creates_a_linked_purchase(client, db_session):
    account_id = _account(client)
    _baseline(client, account_id, ("CW8.PA", "Amundi MSCI World", 10, 100.0))

    div = _dividend(client, account_id, 45.0, quantity=0.5, reinvested=True)
    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(10.5)
    assert h.buy_price_avg == pytest.approx((1000 + 45) / 10.5, rel=1e-4)  # 0,5 part à 90 €

    children = db_session.query(InvestmentTransaction).filter_by(reinvest_of_id=div["id"]).all()
    assert len(children) == 1
    assert children[0].type == "achat"
    assert children[0].unit_price == pytest.approx(90.0)

    # L'achat lié n'est pas modifiable à la main : on passe par le dividende
    assert client.patch(f"/investment-transactions/{children[0].id}", json={"quantity": 9}).status_code == 409
    assert client.delete(f"/investment-transactions/{children[0].id}").status_code == 409

    # Retoucher le libellé ne touche pas à l'achat lié
    assert client.patch(f"/investment-transactions/{div['id']}", json={"note": "Dividende CW8"}).status_code == 200
    assert [c.id for c in db_session.query(InvestmentTransaction).filter_by(reinvest_of_id=div["id"]).all()] == [children[0].id]

    # Modifier les parts du dividende met à jour l'achat et la position
    assert client.patch(f"/investment-transactions/{div['id']}", json={"quantity": 1.0}).status_code == 200
    assert _holding(db_session, account_id).quantity == pytest.approx(11.0)

    # Ne plus réinvestir supprime l'achat
    assert client.patch(f"/investment-transactions/{div['id']}", json={"reinvested": False}).status_code == 200
    assert _holding(db_session, account_id).quantity == pytest.approx(10.0)
    assert db_session.query(InvestmentTransaction).filter_by(reinvest_of_id=div["id"]).count() == 0

    # Supprimer le dividende supprime l'achat lié
    div2 = _dividend(client, account_id, 45.0, quantity=0.5, reinvested=True, days_ago=50)
    assert _holding(db_session, account_id).quantity == pytest.approx(10.5)
    assert client.delete(f"/investment-transactions/{div2['id']}").status_code == 204
    assert _holding(db_session, account_id).quantity == pytest.approx(10.0)
    assert db_session.query(InvestmentTransaction).filter_by(type="achat").count() == 0


# ─── Dividendes existants sans titre ────────────────────────────────────────

def test_link_existing_dividends_by_label(client, db_session):
    account_id = _account(client)
    _baseline(client, account_id, ("AAPL", "Apple Inc.", 1, None), ("TTE", "TotalEnergies SE", 3, None))
    now = datetime.now()
    for note in ("Dividende Apple", "Dividende Total Energie", "Correction Impot"):
        db_session.add(InvestmentTransaction(
            account_id=account_id, date=now - timedelta(days=30), type="dividende", amount=1.0, currency="EUR",
            original_amount=1.0, note=note,
        ))
    db_session.commit()

    # Par défaut on se contente de proposer
    preview = client.post("/investment-transactions/link-dividends", params={"account_id": account_id}).json()
    assert preview["applied"] is False
    assert {m["ticker"] for m in preview["matched"]} == {"AAPL", "TTE"}
    assert [u["note"] for u in preview["unmatched"]] == ["Correction Impot"]
    assert db_session.query(InvestmentTransaction).filter(InvestmentTransaction.ticker.isnot(None)).count() == 0

    applied = client.post("/investment-transactions/link-dividends", params={"account_id": account_id, "dry_run": False}).json()
    assert applied["applied"] is True
    db_session.expire_all()
    assert db_session.query(InvestmentTransaction).filter_by(ticker="AAPL").count() == 1
    assert db_session.query(InvestmentTransaction).filter_by(ticker="TTE").count() == 1
    assert db_session.query(InvestmentTransaction).filter(InvestmentTransaction.ticker.is_(None)).count() == 1
    assert _holding(db_session, account_id, "AAPL").pays_dividends is True


# ─── Agrégats ───────────────────────────────────────────────────────────────

def test_dividend_summary_converts_to_eur_and_computes_yields(client, monkeypatch):
    import app.api.analytics.dividends as dividends_api

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price": 200.0, "price_eur": 200.0} for s in symbols}

    monkeypatch.setattr(dividends_api, "get_market_quotes", fake_quotes)

    account_id = _account(client)
    _baseline(client, account_id, ("CW8.PA", "Amundi MSCI World", 10, 100.0))

    # 10 USD net + 1,5 USD de retenue, à 1 EUR = 2 USD => 5 € net, 0,75 € de retenue
    _dividend(client, account_id, 10.0, currency="USD", withholding_tax=1.5, days_ago=60)
    _dividend(client, account_id, 45.0, days_ago=120)
    _dividend(client, account_id, 40.0, days_ago=800)  # hors des 12 derniers mois et de la fenêtre de 24 mois

    body = client.get("/analytics/dividends", params={"account_id": account_id}).json()
    totals = body["totals"]
    assert totals["count"] == 3
    assert totals["net_eur"] == pytest.approx(90.0)
    assert totals["withholding_eur"] == pytest.approx(0.75)
    assert totals["gross_eur"] == pytest.approx(90.75)
    assert totals["last_12m_eur"] == pytest.approx(50.0)

    (line,) = body["by_ticker"]
    assert line["ticker"] == "CW8.PA"
    assert line["total_eur"] == pytest.approx(90.0)
    assert line["yield_on_cost_pct"] == pytest.approx(5.0)   # 50 € / 1 000 € investis
    assert line["current_yield_pct"] == pytest.approx(2.5)   # 50 € / (10 × 200 €)
    assert sum(m["net_eur"] for m in body["by_month"]) == pytest.approx(50.0)  # 24 mois glissants
    assert sum(y["net_eur"] for y in body["by_year"]) == pytest.approx(90.0)
    assert body["unlinked"]["count"] == 0


def test_holdings_show_dividends_and_total_return(client, monkeypatch):
    import app.api.holdings as holdings_api

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price": 120.0, "price_eur": 120.0, "type": "ETF", "currency": "EUR", "stale": False} for s in symbols}

    monkeypatch.setattr(holdings_api, "get_market_quotes", fake_quotes)

    account_id = _account(client)
    _baseline(client, account_id, ("CW8.PA", "Amundi MSCI World", 10, 100.0))
    _dividend(client, account_id, 50.0, days_ago=60)

    (holding,) = client.get("/holdings", params={"account_id": account_id}).json()
    assert holding["gain_eur"] == pytest.approx(200.0)            # 10 × 120 − 1 000
    assert holding["dividends_received_eur"] == pytest.approx(50.0)
    assert holding["dividends_12m_eur"] == pytest.approx(50.0)
    assert holding["total_return_eur"] == pytest.approx(250.0)
    assert holding["total_return_pct"] == pytest.approx(25.0)
    assert holding["pays_dividends"] is True

    # Le caractère distribuant se règle à la main
    resp = client.put(f"/holdings/{holding['id']}", json={"pays_dividends": False})
    assert resp.status_code == 200
    assert resp.json()["pays_dividends"] is False


# ─── Centre d'Actions ───────────────────────────────────────────────────────

def test_action_center_dividend_reminders(client, db_session):
    account_id = _account(client)
    _baseline(client, account_id, ("CW8.PA", "Amundi MSCI World", 10, 100.0), ("AAPL", "Apple Inc.", 1, None), days_ago=600)
    # CW8 distribue mais son dernier dividende date de 14 mois ; AAPL ne distribue pas ; un dividende sans titre traîne
    _dividend(client, account_id, 5.0, days_ago=430)
    db_session.add(InvestmentTransaction(
        account_id=account_id, date=datetime.now() - timedelta(days=20), type="dividende", amount=1.0,
        currency="EUR", original_amount=1.0, note="Dividende Apple",
    ))
    db_session.commit()

    ids = {a["id"] for a in client.get("/analytics/actions").json()["actions"]}
    assert f"dividend-missing-{account_id}-CW8.PA" in ids
    assert f"dividend-missing-{account_id}-AAPL" not in ids
    assert f"dividends-unlinked-{account_id}" in ids

    # Un dividende récent fait disparaître le rappel
    _dividend(client, account_id, 5.0, days_ago=10)
    ids = {a["id"] for a in client.get("/analytics/actions").json()["actions"]}
    assert f"dividend-missing-{account_id}-CW8.PA" not in ids


@pytest.mark.parametrize("note,expected", [
    ("Bitcoin", "BTC-EUR"),
    ("Achat BTC", "BTC-EUR"),
    ("BTC", "BTC-EUR"),
    ("Ethereum", "ETH-USD"),
    ("ETH", "ETH-USD"),
    ("Ether", "ETH-USD"),
    ("SOL", "SOL-EUR"),
])
def test_match_ticker_for_crypto_pairs(note, expected):
    candidates = [("BTC-EUR", "Bitcoin EUR"), ("ETH-USD", "Ethereum USD"), ("SOL-EUR", "Solana EUR")]
    assert match_dividend_ticker(note, candidates) == expected
