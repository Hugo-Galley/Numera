from datetime import datetime

from sqlalchemy.orm import Session

from app.services.budget import reimbursements as remb
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.reimbursement import ReimbursementClaim
from app.models.transaction import Transaction


def make_account(db: Session, name="Principal"):
    acc = Account(name=name, type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def tx(db: Session, account, type_, amount, day, merchant="x"):
    date = datetime(2026, 9, day)
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


def test_bulk_delete_recalculates_balances_once(client, db_session):
    main = make_account(db_session)
    other = make_account(db_session, "Livret")
    init = tx(db_session, main, "Solde Initial", 1000.0, 1)
    a = tx(db_session, main, "Sortie", 100.0, 2)
    b = tx(db_session, main, "Sortie", 50.0, 3)
    c = tx(db_session, main, "Entree", 20.0, 4)
    d = tx(db_session, other, "Entree", 10.0, 5)

    resp = client.post("/transactions/bulk-delete", json={"ids": [a.id, b.id, d.id, 9999]})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 3}

    db_session.expire_all()
    remaining = db_session.query(Transaction).order_by(Transaction.id).all()
    assert [t.id for t in remaining] == [init.id, c.id]
    assert db_session.get(Transaction, c.id).running_balance == 1020.0


def test_bulk_delete_releases_claims(client, db_session):
    main = make_account(db_session)
    sortie = tx(db_session, main, "Sortie", 90.0, 2, "RESTO")
    entree = tx(db_session, main, "Entree", 30.0, 3)
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.allocate(db_session, claim, entree.id)

    assert client.post("/transactions/bulk-delete", json={"ids": [sortie.id]}).status_code == 200
    db_session.expire_all()
    assert db_session.query(ReimbursementClaim).count() == 0
    assert db_session.get(Transaction, entree.id).reimbursement_offset == 0.0


def test_bulk_delete_both_legs_of_transfer(client, db_session):
    main = make_account(db_session)
    livret = make_account(db_session, "Livret")
    out = tx(db_session, main, "Sortie", 200.0, 2, "VIR LIVRET")
    inc = tx(db_session, livret, "Entree", 200.0, 2, "VIR PRINCIPAL")
    keep = tx(db_session, livret, "Entree", 5.0, 3)
    assert client.post(f"/transactions/{out.id}/link/{inc.id}").status_code == 200

    assert client.post("/transactions/bulk-delete", json={"ids": [out.id, inc.id]}).json() == {"deleted": 2}
    db_session.expire_all()
    assert [t.id for t in db_session.query(Transaction).all()] == [keep.id]
    assert db_session.get(Transaction, keep.id).running_balance == 5.0


def test_delete_recurring_dca_legs(client, db_session):
    """DCA récurrent par virement : chaque côté se supprime et délie l'autre."""
    import asyncio

    from app.services.budget.recurring import generate_recurring_transactions
    from app.models.investment_transaction import InvestmentTransaction
    from app.models.recurring_transaction import RecurringTransaction

    cc = make_account(db_session, "CC")
    pea = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(pea)
    db_session.commit()
    db_session.add(RecurringTransaction(
        account_id=cc.id, name="DCA CW8", type="Sortie", amount=100.0, currency="EUR", frequency="monthly",
        day_of_month=5, start_date=datetime(2026, 7, 5), auto_generate=True, is_active=True,
        transfer_to_account_id=pea.id, ticker="CW8", quantity=0.2, unit_price=500.0,
    ))
    db_session.commit()
    assert asyncio.run(generate_recurring_transactions(db_session)) >= 2

    first, second = db_session.query(InvestmentTransaction).order_by(InvestmentTransaction.id).limit(2).all()
    sortie_of_first = first.linked_transaction_id
    assert client.delete(f"/investment-transactions/{first.id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(Transaction, sortie_of_first).linked_investment_transaction_id is None

    assert client.post("/transactions/bulk-delete", json={"ids": [second.linked_transaction_id]}).status_code == 200
    db_session.expire_all()
    assert db_session.get(InvestmentTransaction, second.id).linked_transaction_id is None
