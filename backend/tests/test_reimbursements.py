from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import reimbursements as remb
from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction


def make_account(db: Session, name="Principal", currency="EUR", type_="courant"):
    acc = Account(name=name, type=type_, currency=currency, active=True)
    db.add(acc)
    db.commit()
    return acc


def tx(db: Session, account, type_, amount, date, merchant="x"):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency=account.currency, running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def resto(db_session: Session):
    main = make_account(db_session)
    sortie = tx(db_session, main, "Sortie", 90.0, datetime(2026, 9, 28), "RESTO LE PETIT")
    return main, sortie


def test_claim_and_allocation_update_offsets(db_session, resto):
    main, sortie = resto
    denis = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.create_claim(db_session, sortie.id, "Julie", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR DENIS")
    alloc = remb.allocate(db_session, denis, entree.id)
    assert alloc.amount == 30.0
    db_session.refresh(sortie); db_session.refresh(entree)
    assert sortie.reimbursement_offset == 30.0
    assert entree.reimbursement_offset == 30.0
    assert remb.claim_received(db_session, denis.id) == 30.0


def test_health_two_refunds_settle_one_claim(db_session, resto):
    main, _ = resto
    consult = tx(db_session, main, "Sortie", 30.0, datetime(2026, 9, 1), "DR MARTIN")
    claim = remb.create_claim(db_session, consult.id, "Sécu + mutuelle", 30.0)
    secu = tx(db_session, main, "Entree", 21.0, datetime(2026, 9, 6), "CPAM")
    mutuelle = tx(db_session, main, "Entree", 9.0, datetime(2026, 9, 12), "MUTUELLE")
    remb.allocate(db_session, claim, secu.id)
    remb.allocate(db_session, claim, mutuelle.id)
    assert remb.claim_received(db_session, claim.id) == 30.0
    db_session.refresh(consult)
    assert consult.reimbursement_offset == 30.0


def test_one_transfer_split_over_two_claims(db_session, resto):
    main, sortie = resto
    cine = tx(db_session, main, "Sortie", 40.0, datetime(2026, 9, 29), "CGR")
    c1 = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    c2 = remb.create_claim(db_session, cine.id, "Denis", 20.0)
    entree = tx(db_session, main, "Entree", 50.0, datetime(2026, 10, 3), "VIR DENIS")
    remb.allocate(db_session, c1, entree.id)
    remb.allocate(db_session, c2, entree.id)
    db_session.refresh(entree)
    assert entree.reimbursement_offset == 50.0
    with pytest.raises(HTTPException) as exc:
        remb.allocate(db_session, c2, entree.id, 25.0)
    assert exc.value.status_code == 400


def test_reallocating_same_entree_updates_amount(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id, 10.0)
    remb.allocate(db_session, claim, entree.id, 25.0)
    assert len(claim.allocations) == 1
    assert remb.claim_received(db_session, claim.id) == 25.0


def test_rules_are_enforced(db_session, resto):
    main, sortie = resto
    usd = make_account(db_session, "Revolut USD", "USD")
    entree_usd = tx(db_session, usd, "Entree", 30.0, datetime(2026, 10, 3))
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    cases = [
        lambda: remb.create_claim(db_session, entree.id, "X", 10.0),        # pas une Sortie
        lambda: remb.create_claim(db_session, sortie.id, "Julie", 70.0),    # 30 + 70 > 90
        lambda: remb.allocate(db_session, claim, sortie.id),                # pas une Entree
        lambda: remb.allocate(db_session, claim, entree_usd.id),            # devise différente
        lambda: remb.allocate(db_session, claim, entree.id, 31.0),          # > attendu
    ]
    for case in cases:
        with pytest.raises(HTTPException) as exc:
            case()
        assert exc.value.status_code == 400
    remb.allocate(db_session, claim, entree.id, 20.0)
    with pytest.raises(HTTPException):
        remb.update_claim(db_session, claim, {"expected_amount": 15.0})     # < reçu
    remb.update_claim(db_session, claim, {"expected_amount": 20.0, "debtor": "Denis M."})
    assert claim.expected_amount == 20.0 and claim.debtor == "Denis M."


def test_transfer_cannot_be_used(db_session, resto):
    main, sortie = resto
    sortie.is_transfer = True
    db_session.commit()
    with pytest.raises(HTTPException):
        remb.create_claim(db_session, sortie.id, "Denis", 30.0)


def test_rounding_three_thirds(db_session, resto):
    main, _ = resto
    dep = tx(db_session, main, "Sortie", 99.99, datetime(2026, 9, 1))
    for name in ("A", "B", "C"):
        remb.create_claim(db_session, dep.id, name, 33.33)
    entree = tx(db_session, main, "Entree", 99.99, datetime(2026, 9, 2))
    db_session.refresh(dep)
    for c in dep.claims:
        remb.allocate(db_session, c, entree.id)
    db_session.refresh(dep)
    assert dep.reimbursement_offset == 99.99


def test_delete_claim_resets_offsets(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    remb.delete_claim(db_session, claim)
    db_session.refresh(sortie); db_session.refresh(entree)
    assert sortie.reimbursement_offset == 0.0 and entree.reimbursement_offset == 0.0
