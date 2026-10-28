import asyncio
from datetime import date, datetime

import pytest

from app.core.finance import month_label_from_date
from app.services.provisions import add_months, compute_states, due_window
from app.models.account import Account
from app.models.category import Category
from app.models.provision import Provision
from app.models.transaction import Transaction


def test_due_window_rolls_forward_and_back():
    anchor = date(2024, 10, 15)
    assert due_window(anchor, 12, date(2026, 10, 26)) == (date(2026, 10, 15), date(2027, 10, 15))
    assert due_window(anchor, 12, date(2026, 10, 15)) == (date(2025, 10, 15), date(2026, 10, 15))
    # Échéance de référence dans le futur lointain : on revient à la prochaine
    assert due_window(date(2030, 3, 1), 6, date(2026, 10, 26)) == (date(2026, 9, 1), date(2027, 3, 1))
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def _tx(db, account, type_, amount, when, category=None):
    t = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type=type_,
        merchant="x", amount=amount, original_amount=amount, currency="EUR", running_balance=amount if type_ == "Solde Initial" else 0.0,
        category_id=category.id if category else None,
    )
    db.add(t)
    db.commit()
    return t


def test_target_and_monthly_needed_without_account(db_session):
    p = Provision(name="Taxe foncière", amount=1200.0, interval_months=12, due_date=date(2026, 10, 15))
    db_session.add(p)
    db_session.commit()

    [st] = asyncio.run(compute_states(db_session, [p], today=date(2027, 4, 15)))

    assert st.next_due == date(2027, 10, 15)
    assert st.monthly_amount == 100.0
    assert st.target_now == pytest.approx(1200.0 * 182 / 365, abs=0.01)
    assert st.status == "untracked"
    assert st.months_left == 6


def test_linked_account_balance_drives_status(db_session):
    livret = Account(name="Livret provisions", type="epargne", currency="EUR", active=True)
    db_session.add(livret)
    db_session.commit()
    _tx(db_session, livret, "Solde Initial", 300.0, datetime(2026, 1, 1))
    p = Provision(name="Assurance auto", amount=1200.0, interval_months=12, due_date=date(2026, 10, 15), account_id=livret.id)
    db_session.add(p)
    db_session.commit()

    [st] = asyncio.run(compute_states(db_session, [p], today=date(2027, 4, 15)))

    assert st.funded == 300.0
    assert st.status == "behind"
    assert st.monthly_needed == pytest.approx((1200.0 - 300.0) / 6, abs=0.01)


def test_last_payment_found_in_category(db_session):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    impots = Category(name="Impôts", type="depense")
    db_session.add_all([courant, impots])
    db_session.commit()
    _tx(db_session, courant, "Sortie", 1150.0, datetime(2026, 10, 12), category=impots)
    p = Provision(name="Taxe foncière", amount=1200.0, interval_months=12, due_date=date(2026, 10, 15), category_id=impots.id)
    db_session.add(p)
    db_session.commit()

    [st] = asyncio.run(compute_states(db_session, [p], today=date(2026, 11, 1)))

    assert st.last_payment == {"date": date(2026, 10, 12), "amount": 1150.0}


def test_crud_and_summary(client, db_session):
    res = client.post("/provisions", json={"name": "Vacances", "amount": 2400, "interval_months": 12, "due_date": "2027-07-01"})
    assert res.status_code == 201
    body = res.json()
    assert body["monthly_amount"] == 200.0
    pid = body["id"]

    assert client.patch(f"/provisions/{pid}", json={"amount": 1200}).json()["monthly_amount"] == 100.0
    summary = client.get("/provisions/summary").json()
    assert summary["monthly_total"] == 100.0

    assert client.post("/provisions", json={"name": "X", "amount": 10, "due_date": "2027-01-01", "category_id": 999}).status_code == 404
    assert client.delete(f"/provisions/{pid}").status_code == 204
    assert db_session.query(Provision).count() == 0
