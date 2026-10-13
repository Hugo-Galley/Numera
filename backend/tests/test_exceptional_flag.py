from datetime import datetime

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction


def _account(db):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db, account, type_, amount, date, merchant="x"):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


def test_patch_sets_and_clears_flag(client, db_session):
    acc = _account(db_session)
    tx = _tx(db_session, acc, "Sortie", 120.0, datetime(2025, 10, 5), "CANAPE")

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})
    assert res.status_code == 200
    assert res.json()["is_exceptional"] is True
    db_session.refresh(tx)
    assert tx.is_exceptional is True

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": False})
    assert res.json()["is_exceptional"] is False


def test_null_flag_is_ignored(client, db_session):
    acc = _account(db_session)
    tx = _tx(db_session, acc, "Sortie", 120.0, datetime(2025, 10, 5), "CANAPE")
    client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": None, "note": "garantie 2 ans"})
    assert res.status_code == 200
    assert res.json()["is_exceptional"] is True
    assert res.json()["note"] == "garantie 2 ans"


def test_flag_leaves_totals_and_balance_unchanged(client, db_session):
    acc = _account(db_session)
    _tx(db_session, acc, "Entree", 1000.0, datetime(2025, 10, 1), "SALAIRE")
    tx = _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 5), "CANAPE")
    params = {"month": 10, "year": 2025}

    before = client.get("/analytics/budget", params=params).json()
    patched = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})
    after = client.get("/analytics/budget", params=params).json()

    assert patched.json()["is_exceptional"] is True
    assert before["depenses_totales"] == after["depenses_totales"] == 100.0
    assert before["depenses_reelles"] == after["depenses_reelles"]
    db_session.refresh(tx)
    assert tx.running_balance == 900.0
