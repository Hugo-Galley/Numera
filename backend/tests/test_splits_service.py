"""Découpage d'une dépense et garde-fous des remboursements : erreurs métier, sans HTTP."""
from datetime import datetime

import pytest

from app.core.errors import InvalidOperationError, NotFoundError
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionSplitItem
from app.services import reimbursements as remb
from app.services.splits import check_split_compatible, set_splits


def _tx(db, type_="Sortie", amount=100.0):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(account)
    db.flush()
    date = datetime(2026, 10, 1)
    tx = Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
                     merchant="x", amount=amount, original_amount=amount, currency="EUR", running_balance=0.0)
    db.add(tx)
    db.commit()
    return tx


def _categories(db):
    a, b = Category(name="Courses", type="depense"), Category(name="Maison", type="depense")
    db.add_all([a, b])
    db.commit()
    return a, b


def test_split_of_income_is_invalid_operation(db_session):
    a, b = _categories(db_session)
    with pytest.raises(InvalidOperationError, match="Seule une dépense \\(hors virement interne\\) peut être découpée"):
        set_splits(db_session, _tx(db_session, "Entree"), [TransactionSplitItem(category_id=a.id, amount=50.0),
                                                          TransactionSplitItem(category_id=b.id, amount=50.0)])


def test_split_with_one_part_is_invalid_operation(db_session):
    a, _ = _categories(db_session)
    with pytest.raises(InvalidOperationError, match="Un découpage compte au moins deux parts"):
        set_splits(db_session, _tx(db_session), [TransactionSplitItem(category_id=a.id, amount=100.0)])


def test_split_on_unknown_category_is_not_found(db_session):
    a, _ = _categories(db_session)
    with pytest.raises(NotFoundError, match="Catégorie 999 introuvable"):
        set_splits(db_session, _tx(db_session), [TransactionSplitItem(category_id=a.id, amount=50.0),
                                                TransactionSplitItem(category_id=999, amount=50.0)])


def test_changing_amount_of_split_expense_is_invalid_operation(db_session):
    a, b = _categories(db_session)
    tx = _tx(db_session)
    set_splits(db_session, tx, [TransactionSplitItem(category_id=a.id, amount=60.0),
                                TransactionSplitItem(category_id=b.id, amount=40.0)])
    with pytest.raises(InvalidOperationError, match="Annulez ou ajustez le découpage avant de changer le montant"):
        check_split_compatible(tx, "Sortie", 120.0, False)


def test_unknown_transaction_claim_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Transaction introuvable"):
        remb.create_claim(db_session, 999, "Denis", 10.0)
