"""Positions dérivées de l'inventaire Point Zéro + opérations, cours stockés en base, devises."""
from datetime import date, datetime, timedelta

import pytest

import app.core.currency as currency_mod
import app.core.market_data as market_data
from app.core.recurring import generate_recurring_transactions
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.recurring_transaction import RecurringTransaction
from app.models.security_price import SecurityPrice


@pytest.fixture(autouse=True)
def offline_market(monkeypatch):
    """Aucun appel réseau : Yahoo ne répond pas, taux historiques fixes (1 EUR = 2 USD)."""
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(market_data, "_fetch_chart", no_chart)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)
    market_data._QUOTES_CACHE.clear()
    yield
    market_data._QUOTES_CACHE.clear()


def _account(client, name="PEA", currency="EUR") -> int:
    resp = client.post("/accounts", json={"name": name, "type": "investissement", "currency": currency, "color": None})
    assert resp.status_code == 201
    return resp.json()["id"]


def _op(client, account_id, type_, qty=None, price=None, *, date="2026-03-01T00:00:00", ticker="CW8.PA",
        amount=None, fees=None, expected=201, **extra):
    payload = {
        "account_id": account_id, "date": date, "type": type_,
        "amount": amount if amount is not None else (qty or 1) * (price or 1),
        "ticker": ticker, "quantity": qty, "unit_price": price, "fees": fees, **extra,
    }
    resp = client.post("/investment-transactions", json=payload)
    assert resp.status_code == expected, resp.text
    return resp.json()


def _holding(db_session, account_id, ticker="CW8.PA"):
    db_session.expire_all()
    return db_session.query(PortfolioHolding).filter_by(account_id=account_id, ticker=ticker).first()


# ─── Rejeu des opérations ───────────────────────────────────────────────────

def test_deleting_an_old_buy_replays_history(client, db_session):
    account_id = _account(client)
    first = _op(client, account_id, "achat", 10, 100.0, date="2026-01-01T00:00:00")
    _op(client, account_id, "achat", 10, 200.0, date="2026-02-01T00:00:00")
    _op(client, account_id, "vente", 5, 250.0, date="2026-03-01T00:00:00")

    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(15)
    assert h.buy_price_avg == pytest.approx(150.0)  # la vente ne change pas le PRU

    # Sans le premier achat : 10 @ 200 puis vente de 5 => 5 @ 200 (l'ancien « reverse » donnait un PRU faux)
    assert client.delete(f"/investment-transactions/{first['id']}").status_code == 204
    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(5)
    assert h.buy_price_avg == pytest.approx(200.0)


def test_selling_everything_removes_the_position_and_rebuy_restarts_pru(client, db_session):
    account_id = _account(client)
    _op(client, account_id, "achat", 10, 100.0, date="2026-01-01T00:00:00")
    _op(client, account_id, "vente", 10, 120.0, date="2026-02-01T00:00:00")
    assert _holding(db_session, account_id) is None

    _op(client, account_id, "achat", 2, 300.0, date="2026-03-01T00:00:00")
    assert _holding(db_session, account_id).buy_price_avg == pytest.approx(300.0)


def test_fees_are_included_in_pru_and_unit_price_is_derived(client, db_session):
    account_id = _account(client)
    # 10 parts pour 1 010 € débités dont 10 € de frais, sans prix unitaire saisi
    tx = _op(client, account_id, "achat", 10, None, amount=1010.0, fees=10.0)
    assert tx["unit_price"] == pytest.approx(100.0)
    assert tx["price_currency"] == "EUR"

    h = _holding(db_session, account_id)
    assert h.buy_price_avg == pytest.approx(101.0)
    assert h.cost_basis_eur == pytest.approx(1010.0)


def test_buy_and_sell_require_ticker_and_quantity(client):
    account_id = _account(client)
    _op(client, account_id, "achat", None, 100.0, ticker=None, amount=100.0, expected=422)
    _op(client, account_id, "vente", 0, 100.0, amount=100.0, expected=422)
    # Les flux d'espèces restent libres
    _op(client, account_id, "versement", None, None, ticker=None, amount=100.0)
    _op(client, account_id, "frais", None, None, ticker=None, amount=2.0)


# ─── Inventaire Point Zéro ──────────────────────────────────────────────────

def _baseline(client, account_id, date, **line):
    item = {"ticker": "CW8.PA", "asset_name": "Amundi MSCI World", "quantity": 10, "currency": "EUR", **line}
    resp = client.post("/holdings/baseline", json={"account_id": account_id, "date": date, "holdings": [item]})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_trades_after_baseline_are_replayed_on_top_of_it(client, db_session):
    account_id = _account(client)
    _op(client, account_id, "achat", 3, 50.0, date="2026-01-15T00:00:00")  # couvert par l'inventaire
    _baseline(client, account_id, "2026-02-01T00:00:00", buy_price_avg=100.0)
    _op(client, account_id, "achat", 10, 200.0, date="2026-03-01T00:00:00")

    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(20)
    assert h.buy_price_avg == pytest.approx(150.0)

    # Une opération sur titre antérieure au Point Zéro est refusée (elle n'aurait aucun effet)
    _op(client, account_id, "achat", 1, 10.0, date="2026-01-20T00:00:00", expected=422)


def test_setting_pru_on_a_baseline_line_updates_the_position(client, db_session):
    account_id = _account(client)
    _baseline(client, account_id, "2026-02-01T00:00:00")  # inventaire sans PRU
    _op(client, account_id, "achat", 10, 200.0, date="2026-03-01T00:00:00")
    h = _holding(db_session, account_id)
    assert h.buy_price_avg is None  # PRU de départ inconnu => PRU inconnu

    resp = client.put(f"/holdings/{h.id}", json={"buy_price_avg": 100.0})
    assert resp.status_code == 200, resp.text
    assert resp.json()["quantity"] == pytest.approx(20)
    assert resp.json()["buy_price_avg"] == pytest.approx(150.0)


def test_position_made_only_of_trades_cannot_be_edited_or_deleted(client, db_session):
    account_id = _account(client)
    _op(client, account_id, "achat", 10, 100.0)
    h = _holding(db_session, account_id)

    assert client.put(f"/holdings/{h.id}", json={"quantity": 3}).status_code == 422
    assert client.delete(f"/holdings/{h.id}").status_code == 409
    # Les métadonnées restent modifiables
    assert client.put(f"/holdings/{h.id}", json={"asset_name": "MSCI World"}).status_code == 200


def test_baseline_line_can_be_deleted(client, db_session):
    account_id = _account(client)
    holdings = _baseline(client, account_id, "2026-02-01T00:00:00")
    assert client.delete(f"/holdings/{holdings[0]['id']}").status_code == 204
    assert _holding(db_session, account_id) is None


# ─── Devises ────────────────────────────────────────────────────────────────

def test_usd_buy_keeps_pru_in_usd_and_cost_in_eur_at_purchase_rate(client, db_session):
    account_id = _account(client, "CTO")
    # 2 actions à 150 USD, montant débité 150 EUR (1 EUR = 2 USD ce jour-là)
    _op(client, account_id, "achat", 2, 150.0, ticker="AAPL", amount=150.0, price_currency="USD")

    h = _holding(db_session, account_id, "AAPL")
    assert h.currency == "USD"
    assert h.buy_price_avg == pytest.approx(150.0)
    assert h.cost_basis_eur == pytest.approx(150.0)


@pytest.mark.anyio
async def test_recurring_buy_uses_quote_currency(db_session):
    account = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    day = datetime.now() - timedelta(days=32)
    db_session.add(SecurityPrice(ticker="AAPL", date=day.date(), close=200.0, currency="USD", source="yahoo"))
    rd = RecurringTransaction(
        account_id=account.id, name="DCA Apple", type="versement", amount=100.0, currency="EUR",
        frequency="monthly", day_of_month=day.day, start_date=day, is_active=True, auto_generate=True,
        ticker="AAPL", quantity=None, unit_price=None,
    )
    db_session.add(rd)
    db_session.commit()

    assert await generate_recurring_transactions(db_session) >= 1

    tx = db_session.query(InvestmentTransaction).filter_by(recurring_transaction_id=rd.id).first()
    # Cours 200 USD = 100 EUR => 100 EUR achètent 1 action ; prix stocké en USD, étiqueté USD
    assert tx.unit_price == pytest.approx(200.0)
    assert tx.price_currency == "USD"
    assert tx.quantity == pytest.approx(1.0)
    h = db_session.query(PortfolioHolding).filter_by(account_id=account.id, ticker="AAPL").first()
    assert h.currency == "USD"
    assert h.buy_price_avg == pytest.approx(200.0)
    assert h.cost_basis_eur == pytest.approx(100.0)


# ─── Cours stockés ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_quote_is_stored_and_used_when_yahoo_fails(db_session, monkeypatch):
    async def chart_ok(client, sym, params):
        return {"meta": {"regularMarketPrice": 512.3, "currency": "EUR", "regularMarketTime": 1780000000}}

    monkeypatch.setattr(market_data, "_fetch_chart", chart_ok)
    quote = (await market_data.get_market_quotes(["CW8.PA"], db=db_session))["CW8.PA"]
    assert quote["price"] == pytest.approx(512.3)
    assert quote["stale"] is False
    assert db_session.query(SecurityPrice).filter_by(ticker="CW8.PA").count() == 1

    async def chart_down(client, sym, params):
        raise RuntimeError("Yahoo down")

    monkeypatch.setattr(market_data, "_fetch_chart", chart_down)
    market_data._QUOTES_CACHE.clear()
    quote = (await market_data.get_market_quotes(["CW8.PA"], db=db_session))["CW8.PA"]
    assert quote["price"] == pytest.approx(512.3)  # dernier cours connu, pas 0
    assert quote["stale"] is True


@pytest.mark.anyio
async def test_price_on_uses_last_close_before_date(db_session):
    db_session.add_all([
        SecurityPrice(ticker="CW8.PA", date=date(2026, 3, 6), close=500.0, currency="EUR", source="yahoo"),
        SecurityPrice(ticker="CW8.PA", date=date(2026, 3, 9), close=510.0, currency="EUR", source="yahoo"),
    ])
    db_session.commit()
    # Samedi 7 mars : clôture du vendredi
    assert (await market_data.get_price_on(db_session, "CW8.PA", date(2026, 3, 7)))["price"] == 500.0
    # Rien d'assez proche (et Yahoo hors ligne) : None
    assert await market_data.get_price_on(db_session, "CW8.PA", date(2025, 1, 1)) is None


def test_guess_quote_currency():
    assert market_data.guess_quote_currency("IE0002XZSHO1.SG") == "EUR"
    assert market_data.guess_quote_currency("BTC-EUR") == "EUR"
    assert market_data.guess_quote_currency("VUSA.L") == "GBP"
    assert market_data.guess_quote_currency("AAPL") == "USD"
