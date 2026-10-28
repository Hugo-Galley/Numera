from datetime import date, datetime

from app.services.salary_generation import check_and_generate_pending_salaries
from app.models.account import Account
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.transaction import Transaction


def _setup(db_session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()
    config = SalaryConfig(salary_account_id=account.id, net_salary=1447.0, is_active=True, created_at=datetime(2026, 6, 1))
    db_session.add(config)
    db_session.commit()
    return account, config


def _salaries(db_session, account_id: int) -> list[Transaction]:
    return db_session.query(Transaction).filter(
        Transaction.account_id == account_id, Transaction.merchant == "Salaire"
    ).all()


def test_pending_month_is_generated_on_pay_day(db_session):
    account, config = _setup(db_session)
    db_session.add(SalaryMonth(salary_config_id=config.id, month_label="2026-10", salary_date=date(2026, 10, 27)))
    db_session.commit()

    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 26)) == 0
    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 27)) == 1
    assert [t.amount for t in _salaries(db_session, account.id)] == [1447.0]


def test_month_flagged_generated_without_transaction_is_regenerated(db_session):
    # Cas réel : mois marqué généré (génération à l'avance, transaction effacée ensuite)
    account, config = _setup(db_session)
    month = SalaryMonth(
        salary_config_id=config.id, month_label="2026-10", salary_date=date(2026, 10, 27), is_generated=True
    )
    db_session.add(month)
    db_session.commit()

    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 27)) == 1
    assert len(_salaries(db_session, account.id)) == 1
    db_session.refresh(month)
    assert month.is_generated

    # Passage suivant de la tâche de fond : rien de plus
    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 27)) == 0
    assert len(_salaries(db_session, account.id)) == 1


def test_manual_salary_entry_prevents_regeneration(db_session):
    account, config = _setup(db_session)
    db_session.add(SalaryMonth(
        salary_config_id=config.id, month_label="2026-10", salary_date=date(2026, 10, 27), is_generated=True
    ))
    db_session.add(Transaction(
        account_id=account.id, date=datetime(2026, 10, 28), month_label="2026-10", type="Entree", merchant="Salaire Axa",
        amount=1420.0, original_amount=1420.0, currency="EUR", running_balance=0.0,
    ))
    db_session.commit()

    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 28)) == 0
    assert len(db_session.query(Transaction).all()) == 1


def test_old_flagged_month_is_left_alone(db_session):
    account, config = _setup(db_session)
    db_session.add(SalaryMonth(
        salary_config_id=config.id, month_label="2026-07", salary_date=date(2026, 7, 25), is_generated=True
    ))
    db_session.commit()

    assert check_and_generate_pending_salaries(db_session, date(2026, 10, 27)) == 0
    assert _salaries(db_session, account.id) == []


def test_summary_reports_flag_without_transaction_as_not_generated(client, db_session):
    _, config = _setup(db_session)
    db_session.add(SalaryMonth(
        salary_config_id=config.id, month_label="2026-11", salary_date=date(2026, 11, 25), is_generated=True
    ))
    db_session.commit()

    assert client.get("/salary/summary/2026/11").json()["is_generated"] is False
