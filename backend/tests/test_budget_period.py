from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.budget import budget_period
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction


def _tx(db: Session, account: Account, when: datetime, tx_type: str, amount: float, merchant: str, **kw) -> Transaction:
    tx = Transaction(
        account_id=account.id, date=when, month_label=month_label_from_date(when), type=tx_type,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0, **kw,
    )
    db.add(tx)
    return tx


@pytest.fixture
def setup(db_session: Session) -> dict:
    db = db_session
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    food = Category(name="Courses", type="depense")
    db.add_all([courant, food])
    db.commit()
    db.add(SalaryConfig(salary_account_id=courant.id, net_salary=2000.0))
    # Salaires les 25 août, 26 septembre ; dépenses réparties de part et d'autre
    _tx(db, courant, datetime(2026, 8, 25), "Entree", 2000.0, "Salaire")
    _tx(db, courant, datetime(2026, 8, 29), "Sortie", 300.0, "Carrefour", category_id=food.id)
    _tx(db, courant, datetime(2026, 9, 10), "Sortie", 500.0, "Carrefour", category_id=food.id)
    _tx(db, courant, datetime(2026, 9, 26), "Entree", 2000.0, "Salaire")
    _tx(db, courant, datetime(2026, 10, 2), "Sortie", 100.0, "Carrefour", category_id=food.id)
    db.commit()
    return {"courant": courant}


def test_period_starts_at_each_salary_and_is_named_after_financed_month(db_session, setup):
    assert budget_period.period_bounds(db_session, 2026, 9) == (datetime(2026, 8, 25), datetime(2026, 9, 26))
    assert budget_period.period_bounds(db_session, 2026, 10)[0] == datetime(2026, 9, 26)


def test_civil_mode_keeps_calendar_months(db_session, setup):
    budget_period.set_mode(db_session, "civil")
    assert budget_period.period_bounds(db_session, 2026, 9) == (datetime(2026, 9, 1), datetime(2026, 10, 1))


def test_without_salary_falls_back_to_civil(db_session):
    assert budget_period.period_bounds(db_session, 2026, 9) == (datetime(2026, 9, 1), datetime(2026, 10, 1))


def test_budget_counts_salary_and_early_spending_in_same_month(client: TestClient, setup):
    september = client.get("/analytics/budget", params={"month": 9, "year": 2026}).json()
    assert september["revenus_totaux"] == 2000.0
    assert september["depenses_totales"] == 800.0
    august = client.get("/analytics/budget", params={"month": 8, "year": 2026}).json()
    assert august["revenus_totaux"] == 0.0


def test_civil_mode_via_api_restores_calendar_totals(client: TestClient, setup):
    res = client.put("/analytics/budget-period", json={"mode": "civil"})
    assert res.status_code == 200
    august = client.get("/analytics/budget", params={"month": 8, "year": 2026}).json()
    assert august["revenus_totaux"] == 2000.0


def test_kpi_history_groups_by_pay_period(client: TestClient, setup):
    rows = client.get("/analytics/kpi-history", params={"months_count": 3}).json()
    by_month = {(r["year"], r["month"]): r for r in rows}
    assert by_month[(2026, 9)]["revenus"] == 2000.0
    assert by_month[(2026, 9)]["depenses"] == 800.0


def test_missing_salary_does_not_stretch_period(db_session: Session, setup):
    courant = setup["courant"]
    _tx(db_session, courant, datetime(2026, 12, 26), "Entree", 2000.0, "Salaire")
    db_session.commit()
    assert budget_period.period_bounds(db_session, 2026, 10) == (datetime(2026, 9, 26), datetime(2026, 10, 26))
    # Le mois sans salaire démarre où la période précédente s'arrête (aucun jour sans période, audit A1)
    assert budget_period.period_bounds(db_session, 2026, 11) == (datetime(2026, 10, 26), datetime(2026, 11, 26))


def test_salary_imported_with_employer_label_is_detected_by_category(db_session: Session):
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    cat = Category(name="Salaire", type="revenu")
    db_session.add_all([courant, cat])
    db_session.commit()
    db_session.add(SalaryConfig(salary_account_id=courant.id, net_salary=2000.0))
    _tx(db_session, courant, datetime(2026, 3, 26), "Entree", 1240.0, "Axa", category_id=cat.id)
    db_session.commit()
    assert budget_period.period_bounds(db_session, 2026, 4)[0] == datetime(2026, 3, 26)


# --- Audit A1 : aucun jour ne doit rester sans période -----------------------------------

def _gap_setup(db: Session, salary_days: list[datetime], expenses: list[tuple[datetime, float]]) -> None:
    courant = Account(name="Courant", type="courant", currency="EUR", active=True)
    db.add(courant)
    db.commit()
    db.add(SalaryConfig(salary_account_id=courant.id, net_salary=2000.0))
    for day in salary_days:
        _tx(db, courant, day, "Entree", 2000.0, "Salaire")
    for day, amount in expenses:
        _tx(db, courant, day, "Sortie", amount, "Carrefour")
    db.commit()


def test_month_without_salary_covers_the_whole_gap(client: TestClient, db_session: Session):
    # Pas de salaire en février : le trou 25/02 → 25/03 doit former le mois de mars
    _gap_setup(
        db_session,
        [datetime(2026, 1, 25), datetime(2026, 3, 25), datetime(2026, 4, 25)],
        [(datetime(2026, 2, 27), 100.0), (datetime(2026, 3, 10), 50.0)],
    )
    start, end = budget_period.period_bounds(db_session, 2026, 3)
    assert start <= datetime(2026, 2, 27) and end > datetime(2026, 3, 10)
    march = client.get("/analytics/budget", params={"month": 3, "year": 2026}).json()
    assert march["depenses_totales"] == 150.0


def test_every_day_belongs_to_exactly_one_period(db_session: Session):
    _gap_setup(
        db_session,
        [datetime(2026, 1, 25), datetime(2026, 3, 25), datetime(2026, 4, 25)],
        [],
    )
    periods = budget_period.build_periods(db_session)
    for before, after in zip(periods, periods[1:]):
        assert before.end == after.start, (before, after)
    assert len({(p.year, p.month) for p in periods}) == len(periods)


def test_second_salary_in_same_financed_month_keeps_coverage(client: TestClient, db_session: Session):
    # Deux salaires (25/01 et 10/02) financent février ; les jours entre 10/02 et 25/02 ne doivent pas disparaître
    _gap_setup(
        db_session,
        [datetime(2026, 1, 25), datetime(2026, 2, 10), datetime(2026, 2, 25)],
        [(datetime(2026, 2, 20), 70.0)],
    )
    periods = budget_period.build_periods(db_session)
    for before, after in zip(periods, periods[1:]):
        assert before.end == after.start, (before, after)
    feb = client.get("/analytics/budget", params={"month": 2, "year": 2026}).json()
    assert feb["depenses_totales"] == 70.0
