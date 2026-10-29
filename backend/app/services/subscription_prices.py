"""Détection des hausses de prix des abonnements et prélèvements réguliers.

Une série = les sorties d'un même compte rattachées à la même récurrence, sinon au même
marchand canonique, sinon au même libellé. Elle est retenue si ses échéances sont
régulières (mensuelle, trimestrielle ou annuelle) ; une hausse est signalée quand le dernier
prélèvement dépasse un montant précédent stable. Aucune écriture : simple lecture.
"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.subscription_prices import LOOKBACK_DAYS, PriceChange, series_change
from app.models.account import Account
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction


def detect_price_changes(db: Session, account_id: int | None = None, now: datetime | None = None) -> list[PriceChange]:
    now = now or datetime.now()
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
            Transaction.date >= now - timedelta(days=LOOKBACK_DAYS),
            Transaction.date <= now,
            (Category.name.is_(None)) | (Category.name.notin_(("Investissement", "Epargne"))),
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    series: dict[tuple, list] = defaultdict(list)
    for row in query.all():
        if row.recurring_transaction_id:
            key = ("r", row.recurring_transaction_id)
        elif row.merchant_id:
            key = ("m", row.merchant_id)
        else:
            key = ("l", (row.merchant or "").strip().lower())
        series[(row.account_id, *key)].append(row)

    changes: list[PriceChange] = []
    for (acc_id, kind, ident), rows in series.items():
        change = series_change(rows, now)
        if change is None:
            continue
        last = rows[-1]
        name = last.recurring_name or last.merchant_name or last.merchant
        changes.append(PriceChange(
            key=f"{kind}{ident}" if kind != "l" else f"l{ident[:60]}",
            name=name,
            account_id=acc_id,
            currency=last.currency or "EUR",
            frequency=change.frequency,
            old_amount=change.old_amount,
            new_amount=change.new_amount,
            changed_on=change.changed_on,
            per_year=change.per_year,
        ))
    changes.sort(key=lambda c: c.changed_on, reverse=True)
    return changes
