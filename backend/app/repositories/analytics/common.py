"""Requêtes et expressions SQL partagées par les analytics."""
from datetime import datetime

from sqlalchemy import and_, func, literal_column, or_, select, union_all
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit

logger = get_logger(__name__)

# Montant « économique » : brut moins la part remboursée (Sortie) ou affectée à une créance (Entree).
# Les KPI de revenus/dépenses l'utilisent ; les flux de trésorerie (soldes, calendrier) restent en brut.
NET_AMOUNT = Transaction.amount - Transaction.reimbursement_offset


def category_lines():
    """Montants nets par (transaction, catégorie), parts de découpage déployées.

    Une transaction sans découpage donne une ligne (sa catégorie, NET_AMOUNT) ; une dépense
    découpée donne une ligne par part, la part remboursée étant répartie au prorata.
    Joindre sur `transaction_id` et grouper sur `category_id` à la place de `Transaction.category_id`
    pour toute répartition par catégorie : la somme des lignes égale la somme des NET_AMOUNT.
    """
    split_tx_ids = select(TransactionSplit.transaction_id)
    whole = select(
        Transaction.id.label("transaction_id"),
        Transaction.category_id.label("category_id"),
        NET_AMOUNT.label("net_amount"),
    ).where(Transaction.id.notin_(split_tx_ids))
    parts = (
        select(
            TransactionSplit.transaction_id.label("transaction_id"),
            TransactionSplit.category_id.label("category_id"),
            (
                TransactionSplit.amount
                * (literal_column("1.0") - Transaction.reimbursement_offset / Transaction.amount)
            ).label("net_amount"),
        )
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
    )
    return union_all(whole, parts).subquery("category_lines")


def income_criterion(db: Session):
    """Ce qui compte comme revenu en vue globale (la requête doit être jointe à `Account`).

    - une entrée sur un compte courant ;
    - une entrée sur un autre compte (livret…) seulement si sa catégorie est de type « revenu »
      (marquage explicite) : un dépôt non lié n'est pas un revenu ;
    - les intérêts (type `Interets`), de nature explicite.
    `Solde Initial` n'en fait jamais partie. Les virements internes sont exclus à part (`is_transfer`).
    """
    revenue_categories = db.query(Category.id).filter(Category.type == "revenu")
    return or_(
        Transaction.type == "Interets",
        and_(
            Transaction.type == "Entree",
            or_(Account.type == "courant", Transaction.category_id.in_(revenue_categories)),
        ),
    )


def budget_versement_ids(db: Session):
    """Versements alimentés par un compte du budget (virement interne lié).

    Seuls ceux-là sont de l'argent « investi » au sens du budget : un versement
    sans virement lié (rapatriement d'un ancien contrat, solde initial,
    intéressement versé directement) n'a pas été prélevé sur les revenus du mois,
    et un couple non lié est déjà compté par la sortie catégorisée.
    """
    return db.query(Transaction.linked_investment_transaction_id).filter(
        Transaction.is_transfer == True,
        Transaction.linked_investment_transaction_id.isnot(None),
    )


def opening_balances_eur(db: Session, start: datetime, end: datetime, rates: dict[str, float]) -> float:
    """Soldes initiaux saisis dans [start, end) sur les comptes actifs, en EUR.

    Ouvrir (ou commencer à suivre) un compte fait apparaître son solde dans le patrimoine
    sans que ce soit un gain : on le retranche des variations de patrimoine.
    """
    rows = (
        db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Solde Initial",
            Transaction.date >= start,
            Transaction.date < end,
            Account.active.is_(True),
        )
        .group_by(Account.currency)
        .all()
    )
    return float(sum(total / rates.get(currency, 1.0) for currency, total in rows))


def savings_account_ids(db: Session) -> list[int]:
    return [acc.id for acc in db.query(Account).filter(Account.type == "epargne", Account.active.is_(True)).all()]


def savings_events_by_account(db: Session, account_ids: list[int], end_date: datetime) -> dict[int, list[tuple[datetime, int, float]]]:
    events: dict[int, list[tuple[datetime, int, float]]] = {acc_id: [] for acc_id in account_ids}
    if not account_ids:
        return events

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id.in_(account_ids), BalanceSnapshot.date <= end_date)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )
    for snap in snapshots:
        events[snap.account_id].append((snap.date, 1, float(snap.current_value)))

    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.date <= end_date)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    for tx in transactions:
        events[tx.account_id].append((tx.date, 0, float(tx.running_balance)))

    for acc_id, items in events.items():
        items.sort(key=lambda item: (item[0], item[1]))
        events[acc_id] = items
    return events


def savings_total_at(db: Session, account_ids: list[int], end_date: datetime) -> float:
    events = savings_events_by_account(db, account_ids, end_date)
    total = 0.0
    for items in events.values():
        total += items[-1][2] if items else 0.0
    return total


def ticket_restaurant_account_ids(db: Session) -> set[int]:
    from app.models.salary_config import SalaryConfig
    ticket_account_ids = set()
    try:
        salary_config = db.query(SalaryConfig).filter(SalaryConfig.is_active == True).first()
        if salary_config and salary_config.ticket_account_id:
            ticket_account_ids.add(salary_config.ticket_account_id)

        matching_accounts = db.query(Account.id).filter(
            (Account.name.ilike("%ticket%restaurant%")) |
            (Account.name.ilike("%tickets%restaurant%")) |
            (Account.type == "ticket_restaurant")
        ).all()
        for acc_id_tuple in matching_accounts:
            ticket_account_ids.add(acc_id_tuple[0])
    except Exception as e:
        logger.warning(f"Error getting ticket restaurant accounts: {e}")

    return ticket_account_ids
