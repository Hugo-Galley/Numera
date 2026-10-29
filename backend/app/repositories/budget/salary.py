from datetime import date

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.salary_month import SalaryMonth
from app.models.telecommuting_day import TelecommutingDay
from app.models.transaction import Transaction

SALARY_MERCHANTS = ["Salaire", "Tickets Restaurant"]


def active_config(db: Session) -> SalaryConfig | None:
    return db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()  # noqa: E712


def active_configs(db: Session) -> list[SalaryConfig]:
    return db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all()  # noqa: E712


def get_recurring(db: Session, recurring_id: int) -> RecurringTransaction | None:
    return db.query(RecurringTransaction).filter_by(id=recurring_id).first()


def disable_recurring(db: Session, recurring_id: int) -> None:
    db.query(RecurringTransaction).filter_by(id=recurring_id).update({"is_active": False, "auto_generate": False})


def months_of_year(db: Session, config_id: int, year: int) -> list[SalaryMonth]:
    return db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config_id,
        SalaryMonth.month_label.startswith(f"{year}-"),
    ).all()


def month_record(db: Session, config_id: int, month_label: str) -> SalaryMonth | None:
    return db.query(SalaryMonth).filter(
        SalaryMonth.salary_config_id == config_id,
        SalaryMonth.month_label == month_label,
    ).first()


def _telecommuting(db: Session, config_id: int, month_label: str):
    return db.query(TelecommutingDay).filter(
        TelecommutingDay.salary_config_id == config_id,
        TelecommutingDay.month_label == month_label,
    )


def telecommuting_days(db: Session, config_id: int, month_label: str) -> list[TelecommutingDay]:
    return _telecommuting(db, config_id, month_label).all()


def count_telecommuting_days(db: Session, config_id: int, month_label: str) -> int:
    return _telecommuting(db, config_id, month_label).count()


def replace_telecommuting_days(db: Session, config_id: int, month_label: str, dates: list[date]) -> None:
    _telecommuting(db, config_id, month_label).delete()
    db.add_all([TelecommutingDay(salary_config_id=config_id, date=d, month_label=month_label) for d in dates])


def salary_transaction(db: Session, salary_recurring_id: int | None, month_label: str) -> Transaction | None:
    return db.query(Transaction).filter(
        Transaction.recurring_transaction_id == salary_recurring_id,
        Transaction.month_label == month_label,
    ).first()


def _orphan_salary_filter(labels: list[str]):
    """Anciennes transactions de salaire ou de tickets sans récurrence."""
    return and_(
        Transaction.merchant.in_(SALARY_MERCHANTS),
        Transaction.month_label.in_(labels),
        Transaction.is_recurring == True,  # noqa: E712
        Transaction.recurring_transaction_id == None,  # noqa: E711
    )


def salary_transactions_for(db: Session, labels: list[str], recurring_ids: list[int]) -> list[Transaction]:
    """Transactions de salaire d'un mois (libellé ISO ou ancien libellé français), récurrentes ou orphelines."""
    return db.query(Transaction).filter(
        Transaction.month_label.in_(labels),
        or_(Transaction.recurring_transaction_id.in_(recurring_ids), _orphan_salary_filter(labels)),
    ).all()


def delete_salary_transactions(db: Session, labels: list[str], recurring_ids: list[int]) -> None:
    for recurring_id in recurring_ids:
        db.query(Transaction).filter(
            Transaction.recurring_transaction_id == recurring_id,
            Transaction.month_label.in_(labels),
        ).delete(synchronize_session="fetch")
    db.query(Transaction).filter(_orphan_salary_filter(labels)).delete(synchronize_session="fetch")
