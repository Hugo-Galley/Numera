"""Non-régression des bugs métier corrigés après l'audit (import, Solde Initial, devises,
virements, positions, soldes de compte, flux)."""
from datetime import datetime

import pytest

from app.core import currency as currency_module
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.models.transaction import Transaction


# ─── Helpers ────────────────────────────────────────────────────────────────

def _account(client, name="Courant", type_="courant", currency="EUR") -> int:
    resp = client.post("/accounts", json={"name": name, "type": type_, "currency": currency, "color": None})
    assert resp.status_code == 201
    return resp.json()["id"]


def _tx(client, account_id, date, type_="Sortie", amount=10.0, merchant="Test", **extra):
    payload = {
        "account_id": account_id,
        "date": date,
        "type": type_,
        "merchant": merchant,
        "amount": amount,
        **extra,
    }
    return client.post("/transactions", json=payload)


def _import(client, account_id, rows):
    header = "Date;Mois;Type;Commercant;Categorie;Montant;Solde Compte"
    content = "\n".join([header, *rows]).encode("utf-8")
    return client.post(
        "/import/commit",
        data={"account_id": str(account_id), "create_missing_categories": "true"},
        files={"file": ("import.csv", content, "text/csv")},
    )


@pytest.fixture()
def no_network(monkeypatch):
    """Frankfurter injoignable + caches de taux vides."""

    class _Down:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            raise RuntimeError("network down")

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(currency_module.httpx, "AsyncClient", _Down)
    monkeypatch.setattr(currency_module, "_rates_cache", {})
    monkeypatch.setattr(currency_module, "_cache_expiry", {})


# ─── Import CSV ─────────────────────────────────────────────────────────────

def test_import_keeps_identical_rows_of_same_file_and_stays_idempotent(client):
    account_id = _account(client)
    rows = [
        "05/03/2026 09:00;Mars;Sortie;Cafe;Sorties;2,50;0",
        "05/03/2026 09:00;Mars;Sortie;Cafe;Sorties;2,50;0",  # deuxième café identique : légitime
    ]
    first = _import(client, account_id, rows).json()
    assert first["imported"] == 2
    assert first["skipped"] == 0

    second = _import(client, account_id, rows).json()
    assert second["imported"] == 0
    assert second["skipped"] == 2


def test_import_rejects_second_solde_initial(client, db_session):
    account_id = _account(client)
    assert _import(client, account_id, ["01/01/2026 00:00;Janvier;Type;Solde initial;Autre;1000,00;1000"]).json()["imported"] == 1

    body = _import(client, account_id, ["01/02/2026 00:00;Fevrier;Type;Autre solde;Autre;500,00;500"]).json()
    assert body["imported"] == 0
    assert body["errors"] == 1
    assert db_session.query(Transaction).filter(Transaction.type == "Solde Initial").count() == 1


# ─── Solde Initial unique et premier ────────────────────────────────────────

def test_solde_initial_cannot_be_created_by_update_bulk_or_late_date(client, db_session):
    account_id = _account(client)
    initial = _tx(client, account_id, "2026-01-01T00:00:00", "Solde Initial", 1000.0, "Solde").json()
    other = _tx(client, account_id, "2026-01-05T00:00:00", "Sortie", 20.0, "Cafe").json()

    # PATCH d'une autre transaction en Solde Initial
    resp = client.patch(f"/transactions/{other['id']}", json={"type": "Solde Initial"})
    assert resp.status_code == 422

    # Bulk
    resp = client.patch("/transactions/bulk", json={"ids": [other["id"]], "type": "Solde Initial"})
    assert resp.status_code == 422

    # Déplacer le Solde Initial après une autre transaction
    resp = client.patch(f"/transactions/{initial['id']}", json={"date": "2026-02-01T00:00:00"})
    assert resp.status_code == 422

    types = sorted(t.type for t in db_session.query(Transaction).all())
    assert types == ["Solde Initial", "Sortie"]

    # Un PATCH neutre du Solde Initial reste possible
    resp = client.patch(f"/transactions/{initial['id']}", json={"note": "ok"})
    assert resp.status_code == 200


# ─── Devises ────────────────────────────────────────────────────────────────

def test_cross_currency_conversion_uses_dated_rates_for_any_pair(monkeypatch):
    import asyncio

    async def fake_historical(db, date, cur, base="EUR"):
        return {"USD": 1.10, "GBP": 0.85, "EUR": 1.0}[cur]

    monkeypatch.setattr(currency_module, "get_historical_rate", fake_historical)
    converted = asyncio.run(
        currency_module.convert_amount(110.0, "USD", "GBP", date=datetime(2026, 1, 1).date(), db=object())
    )
    assert converted == pytest.approx(85.0)


def test_unknown_currency_is_rejected_instead_of_converted_1_to_1(client, db_session, no_network):
    account_id = _account(client)
    resp = _tx(client, account_id, "2026-03-01T00:00:00", "Sortie", 100.0, "Achat", currency="XXX")
    assert resp.status_code == 422
    assert db_session.query(Transaction).count() == 0


def test_offline_fallback_still_converts_known_currencies(client, db_session, no_network):
    account_id = _account(client)
    resp = _tx(client, account_id, "2026-03-01T00:00:00", "Sortie", 108.0, "Achat", currency="USD")
    assert resp.status_code == 201
    assert resp.json()["amount"] == pytest.approx(100.0)  # 108 USD / 1.08
    assert resp.json()["original_amount"] == pytest.approx(108.0)


# ─── Virements ──────────────────────────────────────────────────────────────

def test_link_rejects_self_and_detaches_previous_partner(client, db_session):
    a = _account(client, "A")
    b = _account(client, "B", "epargne")
    out = _tx(client, a, "2026-03-01T10:00:00", "Sortie", 50.0, "Virement").json()
    in1 = _tx(client, b, "2026-03-01T10:00:00", "Entree", 50.0, "Recu 1").json()
    in2 = _tx(client, b, "2026-03-01T11:00:00", "Entree", 50.0, "Recu 2").json()

    assert client.post(f"/transactions/{out['id']}/link/{out['id']}").status_code == 422

    assert client.post(f"/transactions/{out['id']}/link/{in1['id']}").status_code == 200
    assert client.post(f"/transactions/{out['id']}/link/{in2['id']}").status_code == 200

    db_session.expire_all()
    first = db_session.get(Transaction, in1["id"])
    second = db_session.get(Transaction, in2["id"])
    assert first.linked_transaction_id is None and first.is_transfer is False
    assert second.linked_transaction_id == out["id"] and second.is_transfer is True


def test_potential_transfers_use_account_currency_not_entry_currency(client, db_session, monkeypatch):
    async def fake_rates(base="EUR"):
        return {"EUR": 1.0, "USD": 1.08}

    monkeypatch.setattr(currency_module, "get_exchange_rates", fake_rates)
    eur = Account(name="EUR", type="courant", currency="EUR", active=True)
    usd = Account(name="USD", type="epargne", currency="USD", active=True)
    db_session.add_all([eur, usd])
    db_session.commit()
    date = datetime(2026, 6, 1, 12)
    db_session.add_all([
        # 100 EUR sortis ; arrivés sur le compte USD : 108 USD (amount = devise du compte)
        Transaction(account_id=eur.id, date=date, month_label="Juin", type="Sortie", merchant="Vir",
                    amount=100.0, original_amount=100.0, currency="EUR", running_balance=-100.0),
        # currency = devise de saisie d'origine : EUR alors que le compte est en USD
        Transaction(account_id=usd.id, date=date, month_label="Juin", type="Entree", merchant="Vir",
                    amount=108.0, original_amount=100.0, currency="EUR", running_balance=108.0),
    ])
    db_session.commit()

    pairs = client.get("/transactions/potential-transfers", params={"amount_tolerance_pct": 1}).json()
    assert len(pairs) == 1


# ─── Positions ──────────────────────────────────────────────────────────────

def _trade(client, account_id, type_, qty, price, date="2026-03-01T00:00:00", ticker="CW8.PA"):
    resp = client.post(
        "/investment-transactions",
        json={
            "account_id": account_id, "date": date, "type": type_, "amount": qty * price,
            "ticker": ticker, "quantity": qty, "unit_price": price,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _holding(db_session, account_id, ticker="CW8.PA"):
    db_session.expire_all()
    return db_session.query(PortfolioHolding).filter_by(account_id=account_id, ticker=ticker).first()


def test_holding_weighted_average_and_reversal(client, db_session):
    account_id = _account(client, "PEA", "investissement")
    _trade(client, account_id, "versement", 10, 100.0)
    second = _trade(client, account_id, "versement", 10, 200.0, date="2026-04-01T00:00:00")

    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(20)
    assert h.buy_price_avg == pytest.approx(150.0)  # moyenne pondérée, pas le dernier prix

    assert client.delete(f"/investment-transactions/{second['id']}").status_code == 204
    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(10)
    assert h.buy_price_avg == pytest.approx(100.0)


def test_sell_keeps_average_and_dividend_does_not_move_position(client, db_session):
    account_id = _account(client, "PEA", "investissement")
    _trade(client, account_id, "versement", 10, 100.0)
    _trade(client, account_id, "retrait", 4, 120.0, date="2026-04-01T00:00:00")
    _trade(client, account_id, "dividende", 3, 5.0, date="2026-05-01T00:00:00")

    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(6)
    assert h.buy_price_avg == pytest.approx(100.0)


def test_updating_a_trade_updates_the_position(client, db_session):
    account_id = _account(client, "PEA", "investissement")
    trade = _trade(client, account_id, "versement", 10, 100.0)

    resp = client.patch(f"/investment-transactions/{trade['id']}", json={"quantity": 4})
    assert resp.status_code == 200
    h = _holding(db_session, account_id)
    assert h.quantity == pytest.approx(4)


def test_holding_gain_converts_cost_basis_to_eur(client, db_session, monkeypatch):
    async def fake_rates(base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}

    async def fake_quotes(symbols, db=None):
        return {s.upper(): {"price": 100.0, "price_eur": 50.0, "type": "EQUITY"} for s in symbols}

    async def fake_historical_rate(db, date, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    import app.api.holdings as holdings_api
    import app.core.currency as currency_mod

    monkeypatch.setattr(holdings_api, "get_exchange_rates", fake_rates)
    monkeypatch.setattr(holdings_api, "get_market_quotes", fake_quotes)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)

    account_id = _account(client, "CTO", "investissement")
    resp = client.post("/holdings", json={
        "account_id": account_id, "ticker": "AAPL", "asset_name": "Apple",
        "quantity": 10, "buy_price_avg": 100.0, "currency": "USD",
    })
    assert resp.status_code == 201
    body = resp.json()
    # Acheté 10 × 100 USD = 500 EUR (taux 2.0) ; vaut 10 × 50 EUR = 500 EUR => gain nul
    assert body["total_invested_eur"] == pytest.approx(500.0)
    assert body["current_value_eur"] == pytest.approx(500.0)
    assert body["gain_eur"] == pytest.approx(0.0)


def test_etf_profile_matching_ignores_empty_and_short_names(db_session):
    from app.core.market_data import _match_etf_profile
    from app.models.etf_profile import EtfProfile

    db_session.add(EtfProfile(ticker="CW8.PA", name="Amundi MSCI World", aliases="[]"))
    db_session.commit()

    assert _match_etf_profile(db_session, "ZZZZ", None, "") is None
    assert _match_etf_profile(db_session, "ZZZZ", None, "msci") is None
    assert _match_etf_profile(db_session, "ZZZZ", None, "Amundi MSCI World UCITS ETF").ticker == "CW8.PA"


# ─── Soldes et flux ─────────────────────────────────────────────────────────

def test_account_balance_uses_most_recent_source(client, db_session):
    account_id = _account(client)
    _tx(client, account_id, "2026-02-10T00:00:00", "Solde Initial", 500.0, "Solde")
    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime(2026, 1, 1), current_value=100.0))
    db_session.commit()
    # Transaction plus récente que le snapshot : c'est elle qui fait foi
    assert client.get(f"/accounts/{account_id}").json()["balance"] == pytest.approx(500.0)

    db_session.add(BalanceSnapshot(account_id=account_id, date=datetime(2026, 3, 1), current_value=777.0))
    db_session.commit()
    assert client.get(f"/accounts/{account_id}").json()["balance"] == pytest.approx(777.0)


def test_money_flow_excludes_solde_initial_from_income(client):
    account_id = _account(client)
    _tx(client, account_id, "2026-06-01T00:00:00", "Solde Initial", 5000.0, "Solde")
    _tx(client, account_id, "2026-06-05T00:00:00", "Entree", 3000.0, "Salaire")
    data = client.get("/analytics/money-flow", params={"month": 6, "year": 2026}).json()
    assert data["income"] == pytest.approx(3000.0)


def test_account_flow_summary_is_computed_by_backend_without_transfers(client, db_session):
    account_id = _account(client)
    now = datetime.now()
    day = datetime(now.year, now.month, 1, 12)
    for i in range(120):  # plus que la pagination par défaut (100) du frontend
        db_session.add(Transaction(
            account_id=account_id, date=day, month_label="X", type="Sortie", merchant=f"M{i}",
            amount=1.0, original_amount=1.0, currency="EUR", running_balance=0.0,
        ))
    db_session.add(Transaction(
        account_id=account_id, date=day, month_label="X", type="Entree", merchant="Salaire",
        amount=500.0, original_amount=500.0, currency="EUR", running_balance=0.0,
    ))
    db_session.add(Transaction(
        account_id=account_id, date=day, month_label="X", type="Sortie", merchant="Vers epargne",
        amount=1000.0, original_amount=1000.0, currency="EUR", running_balance=0.0, is_transfer=True,
    ))
    db_session.commit()

    data = client.get("/analytics/account-flow-summary", params={"account_id": account_id}).json()
    assert data["monthly_net_flow"] == pytest.approx(500.0 - 120.0)  # virement exclu
    assert data["avg_expense"] == pytest.approx(1.0)
    assert client.get("/analytics/account-flow-summary", params={"account_id": 9999}).status_code == 404


# ─── Import / export robustes ───────────────────────────────────────────────

def test_import_accepts_windows_1252_encoded_csv(client, db_session):
    account_id = _account(client)
    content = "Date;Mois;Type;Commercant;Categorie;Montant;Solde Compte\n05/03/2026;Mars;Sortie;Café Müller;Sorties;3,20;0\n"
    response = client.post(
        "/import/commit",
        data={"account_id": str(account_id), "create_missing_categories": "true"},
        files={"file": ("import.csv", content.encode("cp1252"), "text/csv")},
    )
    assert response.status_code == 200
    assert response.json()["imported"] == 1
    assert db_session.query(Transaction).one().merchant == "Café Müller"


def test_export_neutralizes_spreadsheet_formulas(client, db_session):
    account_id = _account(client)
    assert _tx(client, account_id, "2026-03-01T00:00:00", "Sortie", 5.0, "=HYPERLINK(\"http://evil\")").status_code == 201
    assert _tx(client, account_id, "2026-03-02T00:00:00", "Sortie", 5.0, "Normal").status_code == 201

    body = client.get("/export/transactions.csv").text
    assert "'=HYPERLINK" in body
    assert ";=HYPERLINK" not in body and ",=HYPERLINK" not in body and ',"=HYPERLINK' not in body
    assert "Normal" in body
