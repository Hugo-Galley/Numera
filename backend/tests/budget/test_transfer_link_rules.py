"""Un virement est une Sortie + une Entree (ou un versement) sur deux comptes différents."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction

DAY = datetime(2026, 6, 1, 12, 0)


def _tx(db: Session, account: Account, type_: str, amount: float = 100.0) -> Transaction:
    tx = Transaction(
        account_id=account.id, date=DAY, month_label=month_label_from_date(DAY), type=type_,
        merchant="x", amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )
    db.add(tx)
    db.commit()
    return tx


@pytest.fixture
def accounts(db_session: Session) -> tuple[Account, Account]:
    a = Account(name="Courant", type="courant", currency="EUR", active=True)
    b = Account(name="Livret", type="epargne", currency="EUR", active=True)
    db_session.add_all([a, b])
    db_session.commit()
    return a, b


def _assert_untouched(db_session: Session, *txs: Transaction) -> None:
    db_session.expire_all()
    for tx in txs:
        fresh = db_session.get(Transaction, tx.id)
        assert not fresh.is_transfer
        assert fresh.linked_transaction_id is None


def test_linking_two_sorties_is_refused(client: TestClient, db_session: Session, accounts):
    a, b = accounts
    loyer, courses = _tx(db_session, a, "Sortie"), _tx(db_session, b, "Sortie")
    response = client.post(f"/transactions/{loyer.id}/link/{courses.id}?type=regular")
    assert response.status_code == 422
    _assert_untouched(db_session, loyer, courses)


def test_linking_same_account_is_refused(client: TestClient, db_session: Session, accounts):
    a, _ = accounts
    sortie, entree = _tx(db_session, a, "Sortie"), _tx(db_session, a, "Entree")
    response = client.post(f"/transactions/{sortie.id}/link/{entree.id}?type=regular")
    assert response.status_code == 422
    _assert_untouched(db_session, sortie, entree)


def test_linking_sortie_to_entree_on_two_accounts_works(client: TestClient, db_session: Session, accounts):
    a, b = accounts
    sortie, entree = _tx(db_session, a, "Sortie"), _tx(db_session, b, "Entree")
    assert client.post(f"/transactions/{sortie.id}/link/{entree.id}?type=regular").status_code == 200
    db_session.expire_all()
    assert db_session.get(Transaction, entree.id).is_transfer


def test_patch_cannot_set_transfer_fields(client: TestClient, db_session: Session, accounts):
    a, b = accounts
    sortie, other = _tx(db_session, a, "Sortie"), _tx(db_session, b, "Entree")
    client.patch(f"/transactions/{sortie.id}", json={
        "is_transfer": True, "linked_transaction_id": other.id,
    })
    _assert_untouched(db_session, sortie, other)
