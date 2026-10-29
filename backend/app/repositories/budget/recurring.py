from datetime import datetime

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.salary_config import SalaryConfig
from app.models.transaction import Transaction


def generatable_rules(db: Session) -> list[RecurringTransaction]:
    """Règles actives à génération automatique, hors récurrences gérées par la configuration salaire."""
    salary_managed_ids: set[int] = set()
    for sc in db.query(SalaryConfig).filter(SalaryConfig.is_active == True).all():  # noqa: E712
        salary_managed_ids.update(i for i in (sc.salary_recurring_id, sc.ticket_recurring_id) if i)
    rules = db.query(RecurringTransaction).filter(
        RecurringTransaction.is_active == True,  # noqa: E712
        RecurringTransaction.auto_generate == True,  # noqa: E712
    ).all()
    return [rd for rd in rules if rd.id not in salary_managed_ids]


def get_account(db: Session, account_id: int) -> Account | None:
    return db.query(Account).filter(Account.id == account_id).first()


def get_rule(db: Session, rule_id: int) -> RecurringTransaction | None:
    return db.query(RecurringTransaction).filter(RecurringTransaction.id == rule_id).first()


def list_page(db: Session, skip: int, limit: int) -> list[RecurringTransaction]:
    return db.query(RecurringTransaction).offset(skip).limit(limit).all()


def transfers_due(db: Session, now: datetime) -> list[Transaction]:
    """Sorties de virements récurrents à arrivée différée dont la date d'arrivée est passée."""
    return db.query(Transaction).filter(
        Transaction.transfer_credit_due.isnot(None), Transaction.transfer_credit_due <= now
    ).order_by(Transaction.transfer_credit_due).all()


def detach_rule(db: Session, rule_id: int) -> None:
    """Délie de la règle les opérations générées et la configuration salaire, avant suppression."""
    for column in (Transaction.recurring_transaction_id, InvestmentTransaction.recurring_transaction_id,
                   SalaryConfig.salary_recurring_id, SalaryConfig.ticket_recurring_id):
        db.query(column.class_).filter(column == rule_id).update({column: None}, synchronize_session=False)


def add(db: Session, obj) -> None:
    db.add(obj)
    db.flush()


def delete(db: Session, rule: RecurringTransaction) -> None:
    db.delete(rule)
