"""Dates avec fuseau (ISO « Z » envoyé par le navigateur) sur les opérations d'investissement."""
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction


def _pea(db_session) -> Account:
    acc = Account(name="PEA", type="investissement", currency="EUR")
    db_session.add(acc)
    db_session.commit()
    return acc


def _buy(account_id: int, date: str) -> dict:
    return {
        "account_id": account_id, "date": date, "type": "versement", "amount": 395.12, "currency": "EUR",
        "ticker": "IE0002XZSHO1.SG", "quantity": 55, "unit_price": 7.184, "price_currency": "EUR",
    }


def test_trade_with_utc_date_after_point_zero_is_accepted(client, db_session):
    acc = _pea(db_session)
    r = client.post("/holdings/baseline", json={
        "account_id": acc.id, "date": "2026-10-01T15:54:10",
        "holdings": [{"ticker": "IE0002XZSHO1.SG", "asset_name": "MSCI World", "quantity": 569, "currency": "EUR"}],
    })
    assert r.status_code == 200

    r = client.post("/investment-transactions", json=_buy(acc.id, "2026-10-16T11:18:00.000Z"))
    assert r.status_code == 201, r.text
    tx = db_session.query(InvestmentTransaction).filter_by(account_id=acc.id).one()
    assert tx.date.tzinfo is None and tx.date.isoformat() == "2026-10-16T11:18:00"


def test_trade_with_offset_date_before_point_zero_is_refused(client, db_session):
    acc = _pea(db_session)
    client.post("/holdings/baseline", json={
        "account_id": acc.id, "date": "2026-10-01T15:54:10",
        "holdings": [{"ticker": "IE0002XZSHO1.SG", "asset_name": "MSCI World", "quantity": 569, "currency": "EUR"}],
    })
    r = client.post("/investment-transactions", json=_buy(acc.id, "2026-09-30T10:00:00+02:00"))
    assert r.status_code == 422
    assert "Point Zéro" in r.json()["detail"]


def test_utc_date_compared_to_zero_point_snapshot(client, db_session):
    acc = _pea(db_session)
    r = client.post("/balance-snapshots", json={
        "account_id": acc.id, "date": "2026-10-01T00:00:00Z", "current_value": 1000, "is_zero_point": True,
    })
    assert r.status_code == 201, r.text
    assert db_session.query(BalanceSnapshot).one().date.tzinfo is None

    r = client.post("/investment-transactions", json={**_buy(acc.id, "2026-10-16T11:18:00.000Z"), "ticker": None, "quantity": None})
    assert r.status_code == 201, r.text
