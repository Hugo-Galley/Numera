from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction


def transactions(db: Session, account_ids: list[int]) -> list[Transaction]:
    query = db.query(Transaction)
    if account_ids:
        query = query.filter(Transaction.account_id.in_(account_ids))
    return query.all()


def investment_transactions(db: Session, account_ids: list[int]) -> list[InvestmentTransaction]:
    query = db.query(InvestmentTransaction)
    if account_ids:
        query = query.filter(InvestmentTransaction.account_id.in_(account_ids))
    return query.all()


def category_names(db: Session, category_ids: set[int]) -> dict[int, str]:
    if not category_ids:
        return {}
    return {c.id: c.name for c in db.query(Category).filter(Category.id.in_(list(category_ids))).all()}


def account_names(db: Session, account_ids: set[int]) -> dict[int, str]:
    if not account_ids:
        return {}
    return {a.id: a.name for a in db.query(Account).filter(Account.id.in_(list(account_ids))).all()}
