from datetime import date, datetime

from app.models.account import Account
from app.models.category import Category
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.transaction import Transaction
from app.services.budget.salary_generation import find_missing_salary_months


def _setup(db_session, created_at=datetime(2026, 5, 1)):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    config = SalaryConfig(salary_account_id=account.id, net_salary=2000.0, is_active=True, created_at=created_at)
    db_session.add(config)
    db_session.commit()
    return account, config


def _salary_month(config, label: str, day: int) -> SalaryMonth:
    year, month = map(int, label.split("-"))
    return SalaryMonth(salary_config_id=config.id, month_label=label, salary_date=date(year, month, day), is_generated=True)


def test_month_without_salary_is_reported(db_session):
    _, config = _setup(db_session)
    db_session.add_all([_salary_month(config, "2026-07", 25), _salary_month(config, "2026-08", 25)])
    db_session.commit()

    # Septembre : jour de paie passé, rien de renseigné ; octobre : le 25 n'est pas encore passé
    assert find_missing_salary_months(db_session, date(2026, 10, 20)) == ["2026-09"]


def test_manual_salary_entry_counts_as_received(db_session):
    account, config = _setup(db_session, created_at=datetime(2026, 8, 1))
    salary_cat = Category(name="Salaire", type="revenu")
    db_session.add(salary_cat)
    db_session.add(_salary_month(config, "2026-08", 25))
    db_session.commit()
    db_session.add(Transaction(
        account_id=account.id, date=datetime(2026, 9, 25), month_label="Sep 2026", type="Entree",
        merchant="Axa", category_id=salary_cat.id, amount=1421.25, original_amount=1421.25,
        currency="EUR", running_balance=0.0,
    ))
    db_session.commit()

    assert find_missing_salary_months(db_session, date(2026, 9, 30)) == []


def test_months_before_config_creation_are_ignored(db_session):
    _setup(db_session, created_at=datetime(2026, 9, 10))
    assert find_missing_salary_months(db_session, date(2026, 10, 30)) == ["2026-09", "2026-10"]


def test_action_center_reports_missing_salary(client, db_session):
    today = date.today()
    _setup(db_session, created_at=datetime(today.year - 1, 1, 1))

    response = client.get("/analytics/actions")
    assert response.status_code == 200
    salary_actions = [a for a in response.json()["actions"] if a["id"].startswith("missing-salary-")]
    assert len(salary_actions) == 1
    assert salary_actions[0]["action_url"] == "/recurring?tab=salary"
    assert salary_actions[0]["metadata"]["months"]
