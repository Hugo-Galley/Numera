"""Logique de la revue de fin de mois : bornes, étape 1, top dépenses, lecture « hors exceptionnel ».

Les imports de `app.api.analytics.utils` sont différés dans les fonctions : `app/api/analytics/__init__`
charge `reports.py`, qui importe ce module ; un import au niveau du module créerait un cycle.
"""
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.budget_period import period_bounds
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

# Même liste que budget_analytics : ces catégories ne sont pas de la consommation
INVESTMENT_CATEGORIES = ["Investissement", "Epargne"]
CATEGORIZE_LIMIT = 50
TOP_EXPENSES_LIMIT = 10


def month_bounds(db: Session, year: int, month: int) -> tuple[datetime, datetime]:
    return period_bounds(db, year, month)


def exceptional_expenses(
    db: Session,
    start: datetime,
    end: datetime,
    rates: dict[str, float],
    account_id: int | None = None,
) -> float:
    """Dépenses nettes marquées exceptionnelles, hors catégories d'investissement (déjà exclues des dépenses réelles)."""
    from app.api.analytics.utils import NET_AMOUNT, _get_ticket_restaurant_account_ids

    query = (
        db.query(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.is_exceptional.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows = query.group_by(Account.currency).all()
    return float(sum(total / rates.get(currency, 1.0) for currency, total in rows))


def savings_basis(budget: dict, account_scope: bool = False) -> float:
    """Montant épargné, numérateur du taux d'épargne de `budget_analytics`.

    Vue globale : revenus − dépenses réelles (l'argent investi ou mis de côté compte comme épargné).
    Vue d'un compte : revenus − dépenses du compte.
    """
    if account_scope:
        return float(budget["revenus_apres_depenses"])
    return float(budget["revenus_totaux"]) - float(budget["depenses_reelles"])


def without_exceptional(budget: dict, exceptional: float, account_scope: bool = False) -> dict:
    """Lecture « hors exceptionnel » à partir du dict de `budget_analytics` ; les totaux officiels ne bougent pas.

    Le taux officiel est plafonné à ±100 : on le recalcule depuis les montants bruts, avec le même numérateur
    que `budget_analytics` (vue globale : revenus − dépenses réelles ; vue d'un compte : revenus − dépenses).
    """
    real = float(budget["depenses_reelles"])
    income = float(budget["revenus_totaux"])
    real_excl = real - exceptional
    savings_excl = savings_basis(budget, account_scope) + exceptional
    rate_excl = savings_excl / income * 100.0 if income > 0 else 0.0
    burn_excl = float(budget["burn_rate"]) * (real_excl / real) if real > 0 else 0.0
    return {
        "exceptional_expenses": round(exceptional, 2),
        "real_expenses_excl_exceptional": round(real_excl, 2),
        "savings_excl_exceptional": round(savings_excl, 2),
        "savings_rate_excl_exceptional": round(max(min(rate_excl, 100.0), -100.0), 2),
        "burn_rate_excl_exceptional": round(max(burn_excl, 0.0), 2),
    }


def _review_tx(tx: Transaction) -> dict:
    from app.api.analytics.utils import net_amount

    return {
        "id": tx.id,
        "date": tx.date,
        "merchant": tx.merchant,
        "amount": round(net_amount(tx), 2),
        "category_name": tx.category.name if tx.category else None,
        "is_exceptional": bool(tx.is_exceptional),
    }


def tx_count(db: Session, start: datetime, end: datetime) -> int:
    return db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end).count()


def categorize_step(db: Session, start: datetime, end: datetime) -> dict:
    """Étape 1 : dépenses du mois sans catégorie (mêmes filtres que l'audit, bornés au mois)."""
    from app.api.analytics.utils import NET_AMOUNT

    def scoped(query):
        return query.filter(
            Transaction.category_id.is_(None),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )

    base = scoped(db.query(Transaction))
    count = base.count()
    total = scoped(db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))).scalar()
    items = base.order_by(Transaction.amount.desc(), Transaction.id.asc()).limit(CATEGORIZE_LIMIT).all()
    return {"count": count, "total": round(float(total or 0.0), 2), "items": [_review_tx(t) for t in items]}


def top_expenses(db: Session, start: datetime, end: datetime) -> list[dict]:
    """Plus grosses dépenses nettes du mois (hors virements et investissement), à marquer exceptionnelles."""
    from app.api.analytics.utils import NET_AMOUNT, _get_ticket_restaurant_account_ids

    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            Account.type.in_(["courant", "epargne"]),
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
    )
    tr_accounts = _get_ticket_restaurant_account_ids(db)
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows = query.order_by(NET_AMOUNT.desc(), Transaction.id.asc()).limit(TOP_EXPENSES_LIMIT).all()
    return [_review_tx(t) for t in rows]


def month_fingerprint(db: Session, start: datetime, end: datetime) -> dict[str, dict[str, float]]:
    """Totaux nets du mois par devise de compte (entrées / sorties), sans conversion : insensibles aux taux de change."""
    from app.api.analytics.utils import NET_AMOUNT

    rows = (
        db.query(Account.currency, Transaction.type, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type.in_(["Entree", "Interets", "Sortie"]),
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Account.currency, Transaction.type)
        .all()
    )
    fingerprint: dict[str, dict[str, float]] = {}
    for currency, type_, total in rows:
        bucket = fingerprint.setdefault(currency, {"in": 0.0, "out": 0.0})
        bucket["out" if type_ == "Sortie" else "in"] += float(total)
    return {c: {k: round(v, 2) for k, v in b.items()} for c, b in sorted(fingerprint.items())}
