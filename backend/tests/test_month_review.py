from datetime import datetime

import pytest

from app.core.finance import month_label_from_date
from app.core.month_review import differs
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(db, account, type_, amount, date, merchant="x", category=None, exceptional=False):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None, is_exceptional=exceptional,
    )
    db.add(t)
    db.commit()
    return t


def _courant(db, **kwargs):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True, **kwargs)
    db.add(acc)
    db.commit()
    return acc


def test_monthly_report_exposes_figures_without_exceptional(client, db_session):
    acc = _courant(db_session)
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    _tx(db_session, acc, "Sortie", 200.0, datetime(2025, 10, 20), "CANAPE", courses, exceptional=True)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 500.0
    assert report["exceptional_expenses"] == 200.0
    assert report["real_expenses_excl_exceptional"] == 300.0
    assert report["savings"] == 1500.0
    assert report["savings_excl_exceptional"] == 1700.0
    assert report["savings_rate"] == 75.0
    assert report["savings_rate_excl_exceptional"] == 85.0
    assert report["burn_rate_excl_exceptional"] == pytest.approx(300.0 / 31, abs=0.02)


def test_exceptional_investment_category_not_double_counted(client, db_session):
    acc = _courant(db_session)
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 500.0, datetime(2025, 10, 3), "PEA", invest, exceptional=True)
    _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 4), "BOULANGERIE")

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 100.0  # 600 de dépenses − 500 d'investissement
    assert report["exceptional_expenses"] == 0.0
    assert report["real_expenses_excl_exceptional"] == 100.0


def test_differs_tolerates_small_drift():
    assert differs(1000.0, 1002.0) is False  # 0,2 % : dérive de taux de change
    assert differs(1000.0, 1010.0) is True
    assert differs(0.0, 0.005) is False
    assert differs(0.0, 0.02) is True
