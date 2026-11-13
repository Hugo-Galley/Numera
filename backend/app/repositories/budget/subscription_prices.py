"""Lecture des prélèvements candidats à la détection de hausses de prix d'abonnement."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.repositories.types import Rows


def series_rows(db: Session, since: datetime, latest: datetime, account_id: int | None) -> Rows:
    """Sorties (hors virements, épargne et investissement, hors abonnements ignorés) de `since` à `latest` inclus."""
    query = (
        db.query(
            Transaction.account_id,
            Transaction.date,
            Transaction.amount,
            Transaction.merchant,
            Transaction.merchant_id,
            Transaction.recurring_transaction_id,
            Account.currency,
            Merchant.name.label("merchant_name"),
            RecurringTransaction.name.label("recurring_name"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .outerjoin(RecurringTransaction, Transaction.recurring_transaction_id == RecurringTransaction.id)
        .filter(
            Account.active.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.is_subscription_ignored.is_(False),
            Transaction.date >= since,
            Transaction.date <= latest,
            (Category.name.is_(None)) | (Category.name.notin_(("Investissement", "Epargne"))),
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
    rows: Rows = query.all()
    return rows
