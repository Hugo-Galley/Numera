from datetime import datetime

from app.services.balances import recalculate_running_balances
from app.domain.finance import month_label_from_date
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


def _setup(db):
    acc = _account(db)
    _tx(db, acc, "Solde Initial", 1000, datetime(2026, 9, 1))
    _tx(db, acc, "Sortie", 50, datetime(2026, 10, 5), "Carrefour")
    _tx(db, acc, "Entree", 200, datetime(2026, 10, 10), "Virement Maman")
    return acc


def _reconcile(client, acc, bank_balance, day="2026-10-20"):
    res = client.post(f"/accounts/{acc.id}/reconcile", json={"date": day, "bank_balance": bank_balance})
    assert res.status_code == 200, res.text
    return res.json()


def test_matching_balance_marks_account_verified(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    acc.last_verified_at = datetime(2026, 1, 1)
    db_session.commit()
    body = _reconcile(client, acc, 1150)
    assert body["matches"] is True and body["gap"] == 0 and body["hints"] == []
    db_session.refresh(acc)
    assert acc.last_verified_at > datetime(2026, 1, 1)


def test_balance_is_taken_at_statement_date(client, db_session):
    acc = _setup(db_session)
    _tx(db_session, acc, "Sortie", 30, datetime(2026, 10, 25), "Après relevé")
    recalculate_running_balances(db_session, acc.id)
    body = _reconcile(client, acc, 1150)
    assert body["numera_balance"] == 1150 and body["matches"] is True


def test_gap_is_not_verified(client, db_session):
    acc = _setup(db_session)
    acc.last_verified_at = datetime(2026, 1, 1)
    db_session.commit()
    recalculate_running_balances(db_session, acc.id)
    body = _reconcile(client, acc, 1100)
    assert body["matches"] is False and body["gap"] == -50
    db_session.refresh(acc)
    assert acc.last_verified_at == datetime(2026, 1, 1)


def test_duplicate_explains_gap(client, db_session):
    acc = _setup(db_session)
    _tx(db_session, acc, "Sortie", 50, datetime(2026, 10, 6), "Carrefour")
    recalculate_running_balances(db_session, acc.id)
    body = _reconcile(client, acc, 1150)
    assert body["gap"] == 50
    assert body["hints"][0]["kind"] == "duplicate"
    assert len(body["hints"][0]["transactions"]) == 2


def test_amount_equal_to_gap_is_suggested(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    # Banque à 950 : Numera a 200 de trop → l'entrée de 200
    body = _reconcile(client, acc, 950)
    kinds = [h["kind"] for h in body["hints"]]
    assert "extra_or_missing" in kinds
    hint = body["hints"][kinds.index("extra_or_missing")]
    assert hint["transactions"][0]["merchant"] == "Virement Maman"


def test_wrong_sign_is_suggested(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    # La dépense de 50 était en fait un remboursement : banque = 1150 + 100
    body = _reconcile(client, acc, 1250)
    assert any(h["kind"] == "wrong_sign" and h["transactions"][0]["merchant"] == "Carrefour" for h in body["hints"])


def test_unexplained_gap_falls_back_to_missing(client, db_session):
    acc = _setup(db_session)
    recalculate_running_balances(db_session, acc.id)
    body = _reconcile(client, acc, 1137.42)
    assert [h["kind"] for h in body["hints"]] == ["missing"]


def test_unknown_account_is_404(client):
    res = client.post("/accounts/999/reconcile", json={"date": "2026-10-20", "bank_balance": 10})
    assert res.status_code == 404
