"""Frontière de transaction des soldes : le recalcul ne commit pas, chaque appelant le fait.

Chaque test relit les soldes dans une session NEUVE : un appelant qui oublierait de commiter
après le recalcul laisserait des soldes faux en base.
"""
import json
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.categorization_rule import CategorizationRule
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.services.balances import recalculate_running_balances


def _fresh_balances(db_session, account_id):
    session = sessionmaker(bind=db_session.get_bind())()
    try:
        rows = session.query(Transaction).filter(Transaction.account_id == account_id) \
            .order_by(Transaction.date, Transaction.id).all()
        return [round(t.running_balance, 2) for t in rows]
    finally:
        session.close()


def _account(client, name="Courant", type_="courant"):
    return client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR"}).json()["id"]


def _tx(client, account_id, day, type_, amount, merchant="x"):
    response = client.post("/transactions", json={"account_id": account_id, "date": f"2026-09-{day:02d}T00:00:00",
                                                  "type": type_, "merchant": merchant, "amount": amount})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_recalculate_does_not_commit(db_session):
    account = Account(name="A", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.flush()
    date = datetime(2026, 9, 1)
    tx = Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date), type="Entree",
                     merchant="x", amount=50.0, original_amount=50.0, currency="EUR", running_balance=999.0)
    db_session.add(tx)
    db_session.commit()
    recalculate_running_balances(db_session, account.id)
    db_session.rollback()
    db_session.refresh(tx)
    assert tx.running_balance == 999.0


def test_create_update_delete_persist_balances(client, db_session):
    account_id = _account(client)
    first = _tx(client, account_id, 1, "Entree", 100.0)
    second = _tx(client, account_id, 2, "Sortie", 30.0)
    assert _fresh_balances(db_session, account_id) == [100.0, 70.0]
    client.patch(f"/transactions/{first}", json={"amount": 200.0})
    assert _fresh_balances(db_session, account_id) == [200.0, 170.0]
    third = _tx(client, account_id, 3, "Sortie", 10.0)
    client.delete(f"/transactions/{second}")
    assert _fresh_balances(db_session, account_id) == [200.0, 190.0]
    client.post("/transactions/bulk-delete", json={"ids": [third]})
    assert _fresh_balances(db_session, account_id) == [200.0]


def test_bulk_update_persists_balances(client, db_session):
    account_id = _account(client)
    _tx(client, account_id, 1, "Entree", 100.0)
    tx = _tx(client, account_id, 2, "Sortie", 30.0)
    client.patch("/transactions/bulk", json={"ids": [tx], "type": "Entree"})
    assert _fresh_balances(db_session, account_id) == [100.0, 130.0]


def test_import_persists_balances(client, db_session):
    account_id = _account(client)
    csv = "Date;Type;Commercant;Montant\n01/09/2026;Entree;Salaire;100\n02/09/2026;Sortie;Cafe;3\n"
    files = {"file": ("x.csv", csv.encode(), "text/csv")}
    client.post("/import/commit", data={"account_id": str(account_id)}, files=files)
    assert _fresh_balances(db_session, account_id) == [100.0, 97.0]


def test_rule_application_persists_balances(client, db_session):
    account_id = _account(client)
    _tx(client, account_id, 1, "Sortie", 40.0, merchant="REMBOURSEMENT MUTUELLE")
    db_session.add(CategorizationRule(pattern="mutuelle", transaction_type="Entree"))
    db_session.commit()
    client.post("/categorization-rules/apply-all")
    assert _fresh_balances(db_session, account_id) == [40.0]


def test_salary_paths_persist_balances(client, db_session):
    account_id = _account(client)
    client.post("/salary/config", json={"salary_account_id": account_id, "net_salary": 2000.0, "ticket_employee_share": 5.0})
    client.put("/salary/months/2026/9", json={"salary_date": "2026-09-25"})
    client.post("/salary/generate/2026/9")
    assert _fresh_balances(db_session, account_id) == [2000.0]
    client.put("/salary/telecommuting/2026/9", json={"dates": ["2026-09-01"]})
    assert _fresh_balances(db_session, account_id) == [1995.0]
    client.delete("/salary/generate/2026/9")
    assert _fresh_balances(db_session, account_id) == []


def test_recurring_generation_persists_balances(client, db_session):
    account_id = _account(client)
    _tx(client, account_id, 1, "Entree", 100.0)
    db_session.add(RecurringTransaction(account_id=account_id, name="Abonnement", type="Sortie", amount=10.0,
                                        currency="EUR", frequency="monthly", start_date=datetime(2026, 9, 2),
                                        end_date=datetime(2026, 9, 3), is_active=True, auto_generate=True))
    db_session.commit()
    client.post("/recurring-transactions/trigger")
    assert _fresh_balances(db_session, account_id) == [100.0, 90.0]


def test_transfer_counterpart_persists_balances(client, db_session):
    source, dest = _account(client, "Courant"), _account(client, "Livret", "epargne")
    sortie = _tx(client, source, 5, "Sortie", 50.0)
    client.post(f"/transactions/{sortie}/transfer-counterpart", json={"account_id": dest})
    assert _fresh_balances(db_session, dest) == [50.0]
