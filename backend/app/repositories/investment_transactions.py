"""Opérations d'investissement (`investment_transactions`)."""
from sqlalchemy.orm import Session

from app.models.investment_transaction import InvestmentTransaction


def for_account(db: Session, account_id: int) -> list[InvestmentTransaction]:
    """Opérations d'un compte, dans l'ordre de la base."""
    return db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id).all()
